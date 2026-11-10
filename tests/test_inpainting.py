"""Offline diffusion tests; synthetic SAM evidence, mocked pipeline, no weight downloads."""
from contextlib import ExitStack
from dataclasses import asdict, replace
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image, ImageDraw
import torch

from transcreation.config import InpaintingConfig, load_inpainting_config
from transcreation.contracts import InpaintingInput
from transcreation.stages.inpainting import digest, load_pipeline, prepare_crop, restore_and_composite, run_inpainting, validate_inputs, validate_mask


class InpaintingTests(unittest.TestCase):
    def setUp(self):
        # Reuse the existing synthetic artifact fixture without inheriting its test methods.
        from test_mask_review import MaskReviewTests
        fixture=MaskReviewTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        self.root=fixture.root; self.source=fixture.source; self.seg=fixture.segmentation
        image=self.source/'original.png'; mask=self.source/'mask_1.png'
        self.request=InpaintingInput(str(image),digest(image.read_bytes()),str(self.seg),digest(self.seg.read_bytes()),
                                      str(mask),digest(mask.read_bytes()),1,"Synthetic textured bowl","Explicit synthetic research choice","RESEARCH_ONLY")
        self.config=InpaintingConfig(); self.out=self.root/'generated'

    def fake(self, outcomes=None):
        completed=SimpleNamespace(images=[Image.new("RGB",(512,512),"blue")],nsfw_content_detected=[False])
        pipe=Mock(); pipe.scheduler=SimpleNamespace(config={"beta_start":.00085})
        def result(**kwargs):
            self.assertTrue(torch.is_inference_mode_enabled())
            self.assertEqual(kwargs['generator'].initial_seed(),42)
            return completed
        pipe.side_effect=outcomes if outcomes is not None else result
        return pipe

    def execute(self,pipe):
        with ExitStack() as stack:
            stack.enter_context(patch('transcreation.stages.inpainting.load_pipeline',return_value=pipe))
            for name,value in [('is_available',True),('synchronize',None),('reset_peak_memory_stats',None),
                               ('memory_allocated',0),('mem_get_info',(1000,4000)),('max_memory_allocated',1234),('empty_cache',None)]:
                stack.enter_context(patch('torch.cuda.'+name,return_value=value))
            return run_inpainting(self.request,self.config,self.out)

    def test_existing_config_defaults_and_invalid_settings(self):
        self.assertEqual(load_inpainting_config(Path('configs/inpainting.yaml')),self.config)
        for fields in [{'revision':'main'},{'processing_size':True},{'context_margin':-1},{'seed':True},
                       {'steps':0},{'strength':0},{'guidance_scale':float('nan')},{'model_id':'another model'}]:
            with self.subTest(fields=fields),self.assertRaises(ValueError): replace(self.config,**fields)

    def test_explicit_lower_score_candidate_and_hashes(self):
        image,mask,result,_=validate_inputs(self.request)
        self.assertEqual(mask.size,image.size); self.assertEqual(mask.histogram()[255],result.masks[1].foreground_pixels)
        self.assertEqual(self.request.candidate_index,1)  # not highest score or implicit candidate 0

    def test_research_scope_never_inherited_from_review(self):
        for scope in ['PENDING','PROPOSE','REVIEW','ABSTAIN','ACCEPT_FOR_SEGMENTATION_TEST','APPROVED']:
            with self.subTest(scope=scope),self.assertRaises(ValueError): replace(self.request,scope=scope)
        with self.assertRaises(TypeError): InpaintingInput(**{**asdict(self.request),'image_edit_authorized':True})

    def test_empty_prompt_and_invalid_candidate(self):
        for text in ['', '  ','null','none','N/A']:
            with self.subTest(text=text),self.assertRaises(ValueError): replace(self.request,prompt=text)
        for index in [None,True,-1,1.0]:
            with self.subTest(index=index),self.assertRaises(ValueError): replace(self.request,candidate_index=index)
        with self.assertRaises(ValueError):validate_inputs(replace(self.request,candidate_index=9))

    def test_modified_png_even_when_pixels_unchanged(self):
        p=Path(self.request.mask_file); p.write_bytes(p.read_bytes()+b'altered bytes')
        with self.assertRaisesRegex(ValueError,'mask SHA'):validate_inputs(self.request)

    def test_segmentation_json_hash_mismatch(self):
        self.seg.write_bytes(self.seg.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError,'JSON SHA'):validate_inputs(self.request)

    def test_image_hash_mismatch(self):
        with self.assertRaisesRegex(ValueError,'image SHA'):validate_inputs(replace(self.request,image_sha256='f'*64))

    def test_unrelated_mask_rejected(self):
        other=self.root/'other.png'; other.write_bytes(Path(self.request.mask_file).read_bytes())
        with self.assertRaisesRegex(ValueError,'belong'):validate_inputs(replace(self.request,mask_file=str(other)))

    def test_nonbinary_empty_and_dimension_mismatch(self):
        image=Image.new('RGB',(30,20))
        for mask in [Image.new('L',(30,20),128),Image.new('L',(30,20),0),Image.new('L',(20,30),255),Image.new('RGB',(30,20),'white')]:
            with self.subTest(mode=mask.mode,size=mask.size),self.assertRaises(ValueError):validate_mask(image,mask)

    def test_local_crop_padding_preserves_geometry(self):
        image=Image.new('RGB',(200,100),'white'); mask=Image.new('L',image.size); ImageDraw.Draw(mask).rectangle((90,40,109,49),fill=255)
        processed,pm,g=prepare_crop(image,mask,replace(self.config,context_margin=10))
        self.assertEqual(g['crop_box_xyxy'],[80,30,120,60]); self.assertEqual(g['padding_ltrb'],[0,5,0,5])
        self.assertEqual(processed.size,(512,512)); self.assertEqual(set(pm.tobytes()),{0,255})
        self.assertEqual(g['padded_side'],40)

    def test_edge_crop_is_bounded_and_non_square_source_not_stretched(self):
        image=Image.new('RGB',(300,80)); mask=Image.new('L',image.size); ImageDraw.Draw(mask).rectangle((0,0,20,9),fill=255)
        _,_,g=prepare_crop(image,mask,self.config)
        self.assertEqual(g['crop_box_xyxy'],[0,0,85,74]); self.assertEqual(g['original_dimensions'],[300,80])

    def test_exact_outside_pixels_and_original_resolution(self):
        image,mask,_,_=validate_inputs(self.request); _,_,g=prepare_crop(image,mask,self.config)
        final,restored,region,metrics=restore_and_composite(image,mask,Image.new('RGB',(512,512),'red'),g)
        self.assertEqual(final.size,image.size); self.assertEqual(metrics['changed_outside_mask'],0)
        self.assertEqual(metrics['changed_inside_mask'],mask.histogram()[255])
        self.assertEqual(region.getchannel('A').tobytes(),mask.tobytes())
        self.assertTrue(np.array_equal(np.asarray(final)[np.asarray(mask)==0],np.asarray(image)[np.asarray(mask)==0]))

    def test_restoration_removes_padding_without_distorting_axes(self):
        image=Image.new('RGB',(40,20),'white'); mask=Image.new('L',image.size,255)
        _,_,g=prepare_crop(image,mask,replace(self.config,context_margin=0))
        pixels=np.zeros((512,512,3),dtype=np.uint8); pixels[:128]=[255,0,0]; pixels[384:]=[0,0,255]; pixels[128:384]=[0,255,0]
        _,restored,_,_=restore_and_composite(image,mask,Image.fromarray(pixels),g)
        self.assertEqual(restored.size,(40,20)); self.assertEqual(restored.getpixel((20,10)),(0,255,0))

    def test_invalid_restoration_dimensions_and_crop(self):
        image,mask,_,_=validate_inputs(self.request); _,_,g=prepare_crop(image,mask,self.config)
        with self.assertRaises(ValueError):restore_and_composite(image,mask,Image.new('RGB',(256,256)),g)
        with self.assertRaises(ValueError):restore_and_composite(image,mask,Image.new('RGB',(512,512)),{**g,'crop_box_xyxy':[-1,0,10,10]})

    def test_mocked_success_serialization_and_original_preservation(self):
        originals={p:p.read_bytes() for p in self.source.iterdir() if p.is_file()}
        pipe=self.fake(); result=self.execute(pipe)
        self.assertEqual(result['status'],'COMPLETED'); self.assertFalse(result['human_approved']); self.assertFalse(result['cultural_edit_authorized'])
        self.assertEqual(result['metrics']['changed_outside_mask'],0); self.assertEqual(len(result['attempts']),1)
        self.assertEqual(pipe.call_args.kwargs['strength'],.9); self.assertEqual(pipe.call_args.kwargs['num_inference_steps'],20)
        json.loads((self.out/'inpainting.json').read_text())
        self.assertTrue(all(p.read_bytes()==data for p,data in originals.items()))
        self.assertEqual((self.out/'evidence/mask_1.png').read_bytes(),originals[Path(self.request.mask_file)])

    def test_one_explicit_oom_fallback(self):
        completed=SimpleNamespace(images=[Image.new('RGB',(512,512),'blue')],nsfw_content_detected=[False])
        pipe=self.fake([torch.cuda.OutOfMemoryError('synthetic OOM'),completed]); result=self.execute(pipe)
        self.assertEqual(result['status'],'COMPLETED'); self.assertEqual([x['status'] for x in result['attempts']],['CUDA_OOM','COMPLETED'])
        pipe.enable_sequential_cpu_offload.assert_called_once_with(gpu_id=0)
        self.assertEqual(pipe.call_count,2)

    def test_second_oom_stops_and_preserves_error(self):
        pipe=self.fake([torch.cuda.OutOfMemoryError('first'),torch.cuda.OutOfMemoryError('second')]); result=self.execute(pipe)
        self.assertEqual(result['status'],'ERROR'); self.assertEqual(pipe.call_count,2); self.assertFalse((self.out/'final.png').exists())
        self.assertEqual(result['attempts'][1]['status'],'CUDA_OOM')

    def test_non_oom_pipeline_error_not_retried(self):
        pipe=self.fake([RuntimeError('synthetic pipeline failure')]); result=self.execute(pipe)
        self.assertEqual(result['status'],'ERROR'); self.assertEqual(pipe.call_count,1); self.assertFalse((self.out/'final.png').exists())

    def test_safety_flag_not_claimed_as_success(self):
        pipe=self.fake([SimpleNamespace(images=[Image.new('RGB',(512,512),'black')],nsfw_content_detected=[True])]); result=self.execute(pipe)
        self.assertEqual(result['status'],'ERROR'); self.assertTrue((self.out/'raw_generated_crop.png').exists()); self.assertFalse((self.out/'final.png').exists())

    def test_no_cuda_is_explicit(self):
        with patch('torch.cuda.is_available',return_value=False),patch('transcreation.stages.inpainting.load_pipeline') as loader:
            result=run_inpainting(self.request,self.config,self.out)
        self.assertEqual(result['status'],'ERROR'); loader.assert_not_called()

    def test_loading_failure_audited(self):
        with patch('torch.cuda.is_available',return_value=True),patch('torch.cuda.memory_allocated',return_value=0),patch('torch.cuda.mem_get_info',return_value=(1,4)),patch('torch.cuda.empty_cache'),patch('transcreation.stages.inpainting.load_pipeline',side_effect=OSError('offline load error')):
            result=run_inpainting(self.request,self.config,self.out)
        self.assertEqual(result['status'],'ERROR'); self.assertEqual(result['observations'][0]['type'],'OSError')

    def test_safetensors_only_pinned_loader(self):
        pipe=Mock(); pipe.unet.config.in_channels=9
        with patch('huggingface_hub.snapshot_download',return_value=str(self.root/self.config.revision)),patch('diffusers.StableDiffusionInpaintPipeline.from_pretrained',return_value=pipe) as loader:
            self.assertIs(load_pipeline(self.config),pipe)
        self.assertTrue(loader.call_args.kwargs['use_safetensors']); self.assertEqual(loader.call_args.kwargs['variant'],'fp16')
        pipe.enable_model_cpu_offload.assert_called_once_with(gpu_id=0)

    def test_source_modified_during_loading_blocks_inference(self):
        pipe=self.fake()
        def changed(_):
            self.seg.write_bytes(self.seg.read_bytes()+b'\n'); return pipe
        with patch('torch.cuda.is_available',return_value=True),patch('torch.cuda.memory_allocated',return_value=0),patch('torch.cuda.mem_get_info',return_value=(1,4)),patch('torch.cuda.empty_cache'),patch('transcreation.stages.inpainting.load_pipeline',side_effect=changed):
            result=run_inpainting(self.request,self.config,self.out)
        self.assertEqual(result['status'],'ERROR'); pipe.assert_not_called()

    def test_no_overwrite_and_raw_planner_input_rejected(self):
        self.out.mkdir()
        with self.assertRaises(FileExistsError):run_inpainting(self.request,self.config,self.out)
        with self.assertRaises(TypeError):InpaintingInput(**{'decision':'REVIEW','candidate_edits':[]})


if __name__=='__main__':
    unittest.main()

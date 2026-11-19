"""Synthetic/mocked editor tests only: no weights, cultural ratings or real approvals."""
from contextlib import ExitStack
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
from transcreation.stages.instruction_editor import InstructionEditInput,PINS,CONTROL_PIN,sha,validate_edit,run_editor


class InstructionEditorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        image=Image.new('RGB',(60,40),(100,120,140));mask=np.zeros((40,60),dtype='uint8');mask[10:30,20:40]=255
        image.save(self.root/'source.png');Image.fromarray(mask).save(self.root/'mask.png')
        Image.fromarray(255-mask).save(self.root/'protected.png');image.save(self.root/'control.png')
        self.spec={'scope':'RESEARCH_ONLY','human_approved':False,'source_image_sha256':sha(self.root/'source.png'),
            'source_object':'synthetic original object','target_object':'synthetic replacement','must_preserve':['exterior'],
            'visual_requirements':['not a real cultural evaluation']}
        (self.root/'spec.json').write_text(json.dumps(self.spec))
        self.request=InstructionEditInput(str(self.root/'source.png'),sha(self.root/'source.png'),
            str(self.root/'spec.json'),sha(self.root/'spec.json'),str(self.root/'mask.png'),sha(self.root/'mask.png'),
            str(self.root/'protected.png'),sha(self.root/'protected.png'),(18,8,42,32),'synthetic target',42,
            control_file=str(self.root/'control.png'),control_sha256=sha(self.root/'control.png'))
        self.config={'backend':'SDXL_CONTROLNET_CANNY','model_id':PINS['SDXL_CONTROLNET_CANNY'][0],
            'revision':PINS['SDXL_CONTROLNET_CANNY'][1],'controlnet_id':CONTROL_PIN[0],'controlnet_revision':CONTROL_PIN[1],
            'processing_size':64,'context_margin':2,'steps':2,'guidance_scale':5.,'strength':.99,
            'control_scale':.5,'negative_prompt':'synthetic'}

    def test_valid_source_coordinate_mapping(self):
        image,mask,protected,working,wm,geom,control=validate_edit(self.request,self.config)
        self.assertEqual(image.size,(60,40));self.assertEqual(working.size,(64,64))
        self.assertEqual(geom['crop_box_xyxy'],[18,8,42,32]);self.assertEqual(control.size,working.size)

    def test_wrong_source_hash(self):
        with self.assertRaises(ValueError):validate_edit(replace(self.request,source_sha256='0'*64),self.config)

    def test_tampered_mask(self):
        Image.new('L',(60,40),255).save(self.root/'mask.png')
        with self.assertRaises(ValueError):validate_edit(self.request,self.config)

    def test_protected_overlap(self):
        Image.new('L',(60,40),255).save(self.root/'protected.png')
        with self.assertRaises(ValueError):validate_edit(replace(self.request,protected_sha256=sha(self.root/'protected.png')),self.config)

    def test_invalid_binary_mask(self):
        Image.new('L',(60,40),127).save(self.root/'mask.png')
        with self.assertRaises(ValueError):validate_edit(replace(self.request,mask_sha256=sha(self.root/'mask.png')),self.config)

    def test_crop_mismatch(self):
        with self.assertRaises(ValueError):validate_edit(replace(self.request,crop_box=(0,0,60,40)),self.config)

    def test_backend_identity_and_revision(self):
        for config in ({**self.config,'backend':'unrelated'}, {**self.config,'revision':'main'},
                       {**self.config,'controlnet_revision':'main'}):
            with self.assertRaises(ValueError):validate_edit(self.request,config)

    def test_no_approval_promotion(self):
        for scope in ('AUTOMATED','APPROVED','PROPOSE'):
            with self.assertRaises(ValueError):replace(self.request,scope=scope)
        self.spec['human_approved']=True;(self.root/'spec.json').write_text(json.dumps(self.spec))
        with self.assertRaises(ValueError):validate_edit(replace(self.request,specification_sha256=sha(self.root/'spec.json')),self.config)

    def test_raw_planner_record_rejected(self):
        with self.assertRaises(ValueError):validate_edit({'decision':'PROPOSE'},self.config)

    def test_control_hash_and_dimensions(self):
        with self.assertRaises(ValueError):validate_edit(replace(self.request,control_sha256='0'*64),self.config)
        Image.new('RGB',(2,2)).save(self.root/'control.png')
        with self.assertRaises(ValueError):validate_edit(replace(self.request,control_sha256=sha(self.root/'control.png')),self.config)

    def execute(self,pipe,out='out'):
        with ExitStack() as stack:
            stack.enter_context(patch('transcreation.stages.instruction_editor.load_editor',return_value=pipe))
            for key,value in [('is_available',True),('reset_peak_memory_stats',None),('synchronize',None),
                              ('max_memory_allocated',1234),('empty_cache',None)]:
                stack.enter_context(patch('torch.cuda.'+key,return_value=value))
            return run_editor(self.request,self.config,self.root/out)

    def test_mocked_saved_locality_and_provenance(self):
        class Pipe:
            def __call__(self,**kwargs):
                self.kwargs=kwargs;return SimpleNamespace(images=[Image.new('RGB',(64,64),'red')])
            def maybe_free_model_hooks(self):self.closed=True
        pipe=Pipe();before=sha(self.root/'source.png');result=self.execute(pipe)
        self.assertEqual(result['backend'],'SDXL_CONTROLNET_CANNY');self.assertFalse(result['human_approved'])
        self.assertEqual(result['metrics']['changed_outside_mask'],0)
        self.assertEqual(result['metrics']['changed_in_protected_regions'],0)
        self.assertTrue(pipe.closed);self.assertEqual(sha(self.root/'source.png'),before)
        self.assertEqual(Image.open(self.root/'out/final.png').size,(60,40))
        self.assertIn('control_image',pipe.kwargs);self.assertEqual(result['calls_attempted'],1)

    def test_failure_propagates_and_is_saved(self):
        class Pipe:
            def __call__(self,**kwargs):raise RuntimeError('synthetic inference failure')
            def maybe_free_model_hooks(self):self.closed=True
        pipe=Pipe()
        with self.assertRaisesRegex(RuntimeError,'synthetic'):self.execute(pipe)
        result=json.loads((self.root/'out/result.json').read_text());self.assertEqual(result['status'],'FAILED')
        self.assertEqual(result['error']['type'],'RuntimeError');self.assertTrue(pipe.closed)

    def test_no_overwrite(self):
        out=self.root/'out';out.mkdir();(out/'keep').write_text('existing evidence')
        with self.assertRaises(FileExistsError):self.execute(None)
        self.assertEqual((out/'keep').read_text(),'existing evidence')

    def test_flux_does_not_claim_native_mask(self):
        config={**self.config,'backend':'FLUX_KONTEXT_GGUF','model_id':PINS['FLUX_KONTEXT_GGUF'][0],
                'revision':PINS['FLUX_KONTEXT_GGUF'][1]}
        *_,control=validate_edit(self.request,config);self.assertIsNone(control)

    def test_existing_sd15_delegation(self):
        from test_inpainting import InpaintingTests
        from transcreation.config import InpaintingConfig
        fixture=InpaintingTests();fixture.setUp()
        try:
            with patch('transcreation.stages.inpainting.run_inpainting',return_value={'baseline':'unchanged'}) as call:
                result=run_editor(fixture.request,InpaintingConfig(),self.root/'legacy')
                self.assertEqual(result,{'baseline':'unchanged'});call.assert_called_once()
        finally:fixture.doCleanups()

    def test_mocked_flux_has_no_native_mask_argument(self):
        self.config={**self.config,'backend':'FLUX_KONTEXT_GGUF','model_id':PINS['FLUX_KONTEXT_GGUF'][0],
                     'revision':PINS['FLUX_KONTEXT_GGUF'][1]}
        class Pipe:
            def __call__(self,**kwargs):
                self.kwargs=kwargs;return SimpleNamespace(images=[Image.new('RGB',(64,64),'red')])
        pipe=Pipe();result=self.execute(pipe)
        self.assertNotIn('mask_image',pipe.kwargs);self.assertNotIn('control_image',pipe.kwargs)
        self.assertFalse(result['native_binary_mask_support']);self.assertEqual(result['metrics']['changed_outside_mask'],0)

    def test_tampered_specification(self):
        self.spec['target_object']='changed after preregistration';(self.root/'spec.json').write_text(json.dumps(self.spec))
        with self.assertRaises(ValueError):validate_edit(self.request,self.config)

    def test_bad_output_size_fails(self):
        class Pipe:
            def __call__(self,**kwargs):return SimpleNamespace(images=[Image.new('RGB',(8,8),'red')])
        with self.assertRaises(ValueError):self.execute(Pipe())
        self.assertEqual(json.loads((self.root/'out/result.json').read_text())['status'],'FAILED')

    def test_load_error_does_not_invoke_model(self):
        with (patch('transcreation.stages.instruction_editor.load_editor',side_effect=FileNotFoundError('synthetic missing cache')),
              patch('torch.cuda.is_available',return_value=True),patch('torch.cuda.reset_peak_memory_stats'),patch('torch.cuda.empty_cache')):
            with self.assertRaises(FileNotFoundError):run_editor(self.request,self.config,self.root/'out')
        result=json.loads((self.root/'out/result.json').read_text())
        self.assertEqual(result['calls_attempted'],0);self.assertEqual(result['error']['type'],'FileNotFoundError')

    def test_invalid_processing_budget(self):
        for config in ({**self.config,'processing_size':511},{**self.config,'steps':0},{**self.config,'context_margin':-1}):
            with self.assertRaises(ValueError):validate_edit(self.request,config)

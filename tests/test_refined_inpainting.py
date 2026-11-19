"""Synthetic polygon masks and mocked diffusion only; no human approvals or weights."""
from contextlib import ExitStack, redirect_stdout
from dataclasses import asdict, replace
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from transcreation.config import InpaintingConfig
from transcreation.contracts import InpaintingInput
from transcreation.stages.inpainting import digest, run_inpainting
from transcreation.stages.refined_inpainting import (
    ORIGIN, RefinedMaskInput, rasterize_annotations, run_refined_inpainting, validate_refined_inputs)


class RefinedInpaintingTests(unittest.TestCase):
    def setUp(self):
        from test_inpainting import InpaintingTests
        self.fixture = InpaintingTests(); self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.annotation = self.root/'annotations.json'
        self.mask = self.root/'refined.png'; self.protected = self.root/'protected.png'
        self.doc = {'scope':'RESEARCH_ONLY','mask_origin':ORIGIN,
            'annotation_method':'operator_polygon_trace_with_protected_exclusions',
            'operator':'synthetic operator, not a real approval','human_approved':False,
            'cultural_edit_authorized':False,'source_image_sha256':self.fixture.request.image_sha256,
            'original_dimensions':[60,40],'sam_result_sha256':self.fixture.request.segmentation_sha256,
            'sam_reference_index':1,'sam_reference_mask_sha256':self.fixture.request.mask_sha256,
            'target_definition':'Synthetic small surface only','boundary_reason':'Exclude uncertain surrounding region',
            'editable_polygons':[{'label':'synthetic interior','points':[[12,12],[24,12],[24,22],[12,22]]}],
            'protected_polygons':[{'label':'synthetic protected top','points':[[0,0],[59,0],[59,10],[0,10]]},
                                  {'label':'synthetic protected island','points':[[20,15],[22,15],[22,17],[20,17]]}]}
        self.annotation.write_text(json.dumps(self.doc))
        mask,protected = rasterize_annotations(self.doc,(60,40));mask.save(self.mask);protected.save(self.protected)
        original = asdict(self.fixture.request)
        self.request = RefinedMaskInput(**{**original,'mask_file':str(self.mask),'mask_sha256':digest(self.mask.read_bytes()),
            'annotation_file':str(self.annotation),'annotation_sha256':digest(self.annotation.read_bytes()),
            'protected_mask_file':str(self.protected),'protected_mask_sha256':digest(self.protected.read_bytes()),
            'mask_origin':ORIGIN})
        self.out = self.root/'derived_generation'

    def execute(self, pipe, max_attempts=2):
        with ExitStack() as stack:
            stack.enter_context(patch('transcreation.stages.inpainting.load_pipeline',return_value=pipe))
            for key,value in [('is_available',True),('synchronize',None),('reset_peak_memory_stats',None),
                              ('memory_allocated',0),('mem_get_info',(1000,4000)),('max_memory_allocated',1234),('empty_cache',None)]:
                stack.enter_context(patch('torch.cuda.'+key,return_value=value))
            return run_refined_inpainting(self.request,InpaintingConfig(),self.out,max_attempts=max_attempts)

    def test_manual_origin_distinct_from_original_sam(self):
        _,mask,sam,payload = validate_refined_inputs(self.request)
        self.assertNotEqual(mask.tobytes(),Image.open(self.fixture.request.mask_file).tobytes())
        self.assertEqual(sam.masks[1].foreground_pixels,285)
        self.assertEqual(payload['mask_1.png'],Path(self.fixture.request.mask_file).read_bytes())
        self.assertEqual(payload['refined_mask.png'],self.mask.read_bytes())

    def test_full_region_protection_is_subtracted(self):
        mask,protected = rasterize_annotations(self.doc,(60,40))
        self.assertEqual(mask.getpixel((21,16)),0)
        self.assertEqual(protected.getpixel((21,16)),255)
        self.assertEqual(int(((np.asarray(mask)>0)&(np.asarray(protected)>0)).sum()),0)

    def test_every_pinned_hash_is_enforced(self):
        for key in ('image_sha256','segmentation_sha256','mask_sha256','annotation_sha256','protected_mask_sha256'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_refined_inputs(replace(self.request,**{key:'f'*64}))

    def test_annotation_reference_cannot_change(self):
        for key,value in [('source_image_sha256','f'*64),('sam_reference_index',0),
                          ('sam_reference_mask_sha256','f'*64),('original_dimensions',[40,60])]:
            doc={**self.doc,key:value};self.annotation.write_text(json.dumps(doc))
            req=replace(self.request,annotation_sha256=digest(self.annotation.read_bytes()))
            with self.subTest(key=key),self.assertRaises(ValueError):validate_refined_inputs(req)

    def test_polygon_coordinates_validated_before_rasterization(self):
        for point in [[-1,2],[60,2],[1,40],[True,3],[1.5,4]]:
            doc={**self.doc,'editable_polygons':[{'label':'invalid','points':[point,[12,2],[12,8]]}]}
            with self.subTest(point=point),self.assertRaises(ValueError):rasterize_annotations(doc,(60,40))

    def test_saved_pixel_geometry_cannot_silently_change(self):
        with Image.open(self.mask) as im:
            im.putpixel((13,13),0);im.save(self.mask)
        with self.assertRaisesRegex(ValueError,'polygon geometry'):
            validate_refined_inputs(replace(self.request,mask_sha256=digest(self.mask.read_bytes())))

    def test_protected_region_inclusion_rejected_even_with_new_hash(self):
        with Image.open(self.mask) as im:
            im.putpixel((21,16),255);im.save(self.mask)
        with self.assertRaisesRegex(ValueError,'protected exclusion'):
            validate_refined_inputs(replace(self.request,mask_sha256=digest(self.mask.read_bytes())))

    def test_nonbinary_empty_wrong_size_masks_rejected(self):
        for im in [Image.new('L',(60,40),128),Image.new('L',(60,40),0),Image.new('L',(40,60),255)]:
            im.save(self.mask)
            with self.assertRaises(ValueError):validate_refined_inputs(replace(self.request,mask_sha256=digest(self.mask.read_bytes())))

    def test_no_human_or_permission_escalation(self):
        for update in [{'human_approved':True},{'cultural_edit_authorized':True},{'image_edit_authorized':True}]:
            self.annotation.write_text(json.dumps({**self.doc,**update}))
            with self.assertRaises(ValueError):
                validate_refined_inputs(replace(self.request,annotation_sha256=digest(self.annotation.read_bytes())))
        with self.assertRaises(ValueError):replace(self.request,scope='APPROVED')
        with self.assertRaises(ValueError):replace(self.request,mask_origin='SAM_PREDICTED')

    def test_isolated_from_original_and_guided_routes(self):
        from transcreation.guided_research import ResearchInput
        with self.assertRaises(ValueError):run_inpainting(self.request,InpaintingConfig(),self.out)
        with self.assertRaises(TypeError):InpaintingInput(**asdict(self.request))
        with self.assertRaises(TypeError):ResearchInput(**asdict(self.request))

    def test_mocked_generation_uses_actual_refined_mask_and_original_resolution(self):
        before={p:p.read_bytes() for p in self.fixture.source.iterdir() if p.is_file()}
        pipe=self.fixture.fake();report=self.execute(pipe)
        self.assertEqual(report['status'],'COMPLETED')
        self.assertEqual(report['editing_mask']['origin'],ORIGIN)
        self.assertEqual(report['editing_mask']['original_sam_reference_mask_sha256'],self.fixture.request.mask_sha256)
        self.assertFalse(report['human_approved']);self.assertFalse(report['cultural_edit_authorized'])
        with Image.open(self.fixture.request.source_image) as source,Image.open(self.out/'final.png') as final,Image.open(self.mask) as mask:
            self.assertEqual(final.size,(60,40))
            changed=np.any(np.asarray(source)!=np.asarray(final),axis=2)
            self.assertEqual(int((changed&(np.asarray(mask)==0)).sum()),0)
            self.assertGreater(int((changed&(np.asarray(mask)==255)).sum()),0)
        self.assertTrue(all(p.read_bytes()==raw for p,raw in before.items()))

    def test_real_error_propagation_without_retry_or_false_success(self):
        pipe=self.fixture.fake([RuntimeError('synthetic pipeline error')])
        report=self.execute(pipe)
        self.assertEqual(report['status'],'ERROR');self.assertEqual(pipe.call_count,1)
        self.assertFalse((self.out/'final.png').exists())

    def test_input_modified_during_loading_stops_before_generation(self):
        def loader(_):
            self.mask.write_bytes(self.mask.read_bytes()+b'changed')
            return self.fixture.fake()
        with patch('transcreation.stages.inpainting.load_pipeline',side_effect=loader),patch('torch.cuda.is_available',return_value=True),patch('torch.cuda.memory_allocated',return_value=0),patch('torch.cuda.mem_get_info',return_value=(1,4)),patch('torch.cuda.empty_cache'):
            report=run_refined_inpainting(self.request,InpaintingConfig(),self.out)
        self.assertEqual(report['status'],'ERROR');self.assertEqual(report['attempts'],[])

    def test_prior_output_cannot_be_overwritten(self):
        self.out.mkdir();sentinel=self.out/'keep.txt';sentinel.write_text('unchanged')
        with self.assertRaises(FileExistsError):run_refined_inpainting(self.request,InpaintingConfig(),self.out)
        self.assertEqual(sentinel.read_text(),'unchanged')

    def test_cli_explicit_refined_input_dispatch(self):
        from scripts.inpaint import main
        path=self.root/'request.json';path.write_text(json.dumps(asdict(self.request)))
        with patch('transcreation.stages.refined_inpainting.run_refined_inpainting',return_value={'status':'COMPLETED'}) as run,redirect_stdout(StringIO()):
            main(['--refined-input',str(path),'--out',str(self.out)])
        self.assertIsInstance(run.call_args.args[0],RefinedMaskInput)

    def test_negative_prompt_only_when_explicitly_supplied_for_research(self):
        self.request=replace(self.request,negative_prompt='text, labels, watermark')
        pipe=self.fixture.fake();report=self.execute(pipe)
        self.assertEqual(pipe.call_args.kwargs['negative_prompt'],'text, labels, watermark')
        self.assertEqual(report['settings']['negative_prompt'],'text, labels, watermark')
        self.assertFalse(report['human_approved'])

    def test_absent_negative_prompt_preserves_existing_call_options(self):
        pipe=self.fixture.fake();report=self.execute(pipe)
        self.assertNotIn('negative_prompt',pipe.call_args.kwargs)
        self.assertIsNone(report['settings']['negative_prompt'])
        with self.assertRaises(TypeError):
            InpaintingInput(**{**asdict(self.fixture.request),'negative_prompt':'text'})

    def test_invalid_negative_prompts_rejected_without_model_dispatch(self):
        for value in [True,[],{},'', '  ','null','none','N/A']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                replace(self.request,negative_prompt=value)

    def test_bounded_research_oom_cannot_exceed_one_call(self):
        import torch
        pipe=self.fixture.fake([torch.cuda.OutOfMemoryError('synthetic OOM at exhausted budget')])
        report=self.execute(pipe,max_attempts=1)
        self.assertEqual(report['status'],'ERROR')
        self.assertEqual(pipe.call_count,1)
        self.assertEqual(len(report['attempts']),1)
        pipe.enable_sequential_cpu_offload.assert_not_called()
        self.assertIsNone(report['settings']['allowed_oom_fallback'])

    def test_invalid_attempt_limits_rejected_before_loading(self):
        for value in (0,3,True):
            with self.subTest(value=value),self.assertRaises(ValueError):
                run_refined_inpainting(self.request,InpaintingConfig(),self.out,max_attempts=value)


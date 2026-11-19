"""Synthetic uncertainty reviews only; no real reviewer decisions or model inference."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import asdict, replace
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from scripts.review_grounding import digest
from scripts.review_uncertainty import DECLARATIONS, PERMISSIONS, check, decide, main, prepare, verify
from transcreation.config import PlannerConfig
from transcreation.contracts import CaptionStatus, PlanningInput, VerifiedObject
from transcreation.orchestration import IntentReference, PipelineInput, PipelineState, run_pipeline
from transcreation.stages.caption import SmolCaptionResult
from transcreation.stages import planning as policy
from transcreation.stages.ollama_planner import OllamaPlanner, SYSTEM_PROMPT


class UncertaintyReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.image=self.root/'image.png'
        Image.new('RGB',(80,60),'white').save(self.image)
        self.request=PlanningInput('A red ceramic cup is on a table.',CaptionStatus.COMPLETE,'test target',
            user_instructions='Change the exterior finish; preserve table and lighting.',
            verified_objects=(VerifiedObject('cup-1','red ceramic cup'),))
        self.raw={'decision':'PROPOSE','decision_reason':'Synthetic user-directed draft only.',
            'scene_summary':'The caption reports a red ceramic cup on a table.',
            'candidate_edits':[{'object_description':'red ceramic cup','localization_phrase':'red ceramic cup',
                'proposed_change':'blue exterior finish','cultural_reason':'Synthetic contextual user preference only.',
                'identity_uncertain':False,'verified_object_id':'cup-1'}],
            'must_preserve':['table','lighting'],'uncertainties':['Review the proposed finish against the original photograph.'],
            'verification_requirements':['Check the finish in a later controlled experiment.']}
        self.counter=0;self.case=self.build()
        self.pending=prepare(self.case,self.image,0,self.root/'review')
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.model_mocks=[self.stack.enter_context(patch(name)) for name in (
            'transcreation.orchestration.create_captioner',
            'transcreation.stages.ollama_planner.OllamaPlanner.plan',
            'transcreation.stages.grounding.GroundingDetector',
            'transcreation.stages.segmentation.SamSegmenter',
            'transcreation.stages.inpainting.run_inpainting')]
        self.addCleanup(self.assert_no_models)

    def assert_no_models(self):
        for model in self.model_mocks:model.assert_not_called()

    def build(self, raw=None, request=None):
        self.counter+=1;case=self.root/f'evidence_{self.counter}';case.mkdir()
        request=request or self.request;raw=deepcopy(raw or self.raw)
        # Produce a native-format synthetic audit without invoking a planner/model.
        draft,initial=policy.parse_model_draft(raw)
        final,issues=policy.validate_planning_result(request,draft,initial)
        config=asdict(PlannerConfig());model={'name':config['model'],'digest':'SYNTHETIC_TEST_ONLY'}
        body={'model':config['model'],'stream':False,'format':{},'options':config['options'],'keep_alive':0,
              'messages':[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':json.dumps(asdict(request))}]}
        response={'model':config['model'],'done':True,'done_reason':'stop',
                  'message':{'role':'assistant','content':json.dumps(raw)}}
        audit={'fixture_scope':'SYNTHETIC_TEST_ONLY','input':asdict(request),'request':body,'config':config,
            'resolved_model':model,'response':response,'raw_planning_result':raw,'planning_result':asdict(final),
            'parse_issues':initial,'validation':{'status':'valid','raw_schema_valid':not initial,'issues':issues,
                'automatically_authorized':False,'rejected_candidates':[{'candidate_index':i,'raw_proposal':edit,
                    'issue_codes':list(dict.fromkeys(v['code'] for v in issues if v['candidate_index'] in (None,i)))}
                    for i,edit in enumerate(raw['candidate_edits'])] if final.decision=='REVIEW' else []}}
        caption=SmolCaptionResult(request.source_caption,'SYNTHETIC_TEST_ONLY',image_dimensions=(80,60),
            eos_reached=request.caption_status==CaptionStatus.COMPLETE,
            token_ceiling_reached=request.caption_status==CaptionStatus.TRUNCATED)
        confirmation={'evidence_type':'SYNTHETIC_TEST_ONLY','source_image_sha256':digest(self.image.read_bytes()),
            'confirmed_object':{'object_id':'cup-1','description':'red ceramic cup'},
            'verbatim_user_confirmation':'Synthetic source-confirmation fixture, not actual human approval.',
            'image_edit_authorized':False,'source_verification_provided_by_actual_user':False}
        def save(name,value):(case/name).write_text(json.dumps(value,indent=2),encoding='utf8')
        save('planning_input.json',asdict(request));save('planner_audit.json',audit)
        save('validated_plan.json',{'planning_result':asdict(final),'issues':issues})
        save('saved_caption.json',{**asdict(caption),'input_sha256':digest(self.image.read_bytes())})
        save('human_confirmation.json',confirmation);save('raw_response_before_validation.json',response)
        (case/'raw_qwen_message.txt').write_bytes(response['message']['content'].encode())
        save('experiment_frozen.json',{'source_image_sha256':digest(self.image.read_bytes()),'dimensions':[80,60],'format':'PNG',
            'planning_input':asdict(request),'planning_input_sha256':digest((case/'planning_input.json').read_bytes()),
            'saved_caption_sha256':digest((case/'saved_caption.json').read_bytes()),
            'human_confirmation_sha256':digest((case/'human_confirmation.json').read_bytes()),
            'validator_source_sha256':digest(Path(policy.__file__).read_bytes()),
            'predeclared_expected_request':body,'config':config,'model':model,'schema':{},
            'new_system_prompt_sha256':digest(SYSTEM_PROMPT.encode())})
        return case

    def mutate(self,path,change):
        value=json.loads(path.read_text(encoding='utf8'));change(value)
        path.write_text(json.dumps(value),encoding='utf8')

    def classify(self, decision='ROUTINE_VERIFICATION_REQUIRED', **changes):
        values={'reviewer':'synthetic test reviewer','reason':'Synthetic judgment: this is a routine pre-edit check, not an unresolved source fact.',
                **{flag:True for flag in DECLARATIONS}}
        values.update(changes)
        return decide(self.pending,self.pending.with_name('decision.json'),decision,**values)

    def test_valid_pending_has_no_fabricated_human_decision(self):
        record=verify(self.pending)
        self.assertEqual(record['decision'],'PENDING');self.assertIsNone(record['reviewer'])
        self.assertIsNone(record['reviewed_at_utc']);self.assertEqual(record['evidence_scope'],'SYNTHETIC_TEST_ONLY')
        self.assertEqual(record['original_uncertainties'],self.raw['uncertainties'])
        self.assertEqual(record['user_instructions'],self.request.user_instructions)
        self.assertTrue(all(record[flag] is False for flag in DECLARATIONS))

    def test_explicit_routine_classification_never_releases_candidate(self):
        record=verify(self.classify())
        self.assertEqual(record['decision'],'ROUTINE_VERIFICATION_REQUIRED')
        self.assertEqual(record['original_validated_decision'],'REVIEW')
        self.assertEqual(record['original_released_candidate_count'],0)
        self.assertTrue(all(record[name] is False for name in PERMISSIONS))

    def test_material_unresolved_is_separate_evidence(self):
        self.assertEqual(verify(self.classify('MATERIAL_UNRESOLVED'))['decision'],'MATERIAL_UNRESOLVED')

    def test_reject_is_not_candidate_release(self):
        self.assertFalse(verify(self.classify('REJECT'))['candidate_release_authorized'])

    def test_needs_review_records_no_execution_permission(self):
        self.assertFalse(verify(self.classify('NEEDS_REVIEW'))['grounding_authorized'])

    def test_missing_and_placeholder_reviewer_rejected(self):
        for name in (None,'','YOUR_NAME','your-name','<name>','reviewer','unknown'):
            with self.subTest(name=name),self.assertRaises((ValueError,TypeError)):
                self.classify(reviewer=name)

    def test_missing_or_nonboolean_inspection_declarations_rejected(self):
        for flag in DECLARATIONS:
            for value in (False,None,1):
                with self.subTest(flag=flag,value=value),self.assertRaises(ValueError):self.classify(**{flag:value})

    def test_empty_placeholder_or_bare_classification_reason_rejected(self):
        for reason in ('',' ','null','N/A','YOUR_REASON','ROUTINE_VERIFICATION_REQUIRED','ok','<explanation>'):
            with self.subTest(reason=reason),self.assertRaises(ValueError):self.classify(reason=reason)

    def test_changed_source_image_hash_rejected(self):
        image=self.pending.parent/'original.webp';image.write_bytes(image.read_bytes()+b' ')
        with self.assertRaises(ValueError):verify(self.pending)

    def test_changed_audit_hash_rejected(self):
        path=self.pending.parent/'planner_audit.json';path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(ValueError):verify(self.pending)

    def test_changed_validated_result_hash_rejected(self):
        path=self.pending.parent/'validated_plan.json';path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(ValueError):verify(self.pending)

    def test_changed_uncertainty_text_rejected(self):
        self.mutate(self.pending,lambda v:v.update(original_uncertainties=['Rewritten to appear routine.']))
        with self.assertRaises(ValueError):verify(self.pending)

    def test_invalid_index_cannot_default_to_zero(self):
        for index in (None,True,-1,1):
            with self.subTest(index=index),self.assertRaises(ValueError):
                prepare(self.case,self.image,index,self.root/'invalid_index')

    def test_changed_record_verified_object_id_rejected(self):
        self.mutate(self.pending,lambda v:v['verified_object'].update(object_id='invented'))
        with self.assertRaises(ValueError):verify(self.pending)

    def test_all_independent_blockers_remain_ineligible(self):
        mutations=(
            lambda p:p['candidate_edits'][0].update(object_description='different object'),
            lambda p:p['candidate_edits'][0].update(localization_phrase='blue exterior finish'),
            lambda p:p['candidate_edits'][0].update(proposed_change='red ceramic cup'),
            lambda p:p['candidate_edits'][0].update(verified_object_id='missing'),
            lambda p:p['candidate_edits'][0].update(verified_object_id=None),
            lambda p:p['candidate_edits'][0].update(identity_uncertain=True),
            lambda p:p.update(scene_summary='The scene contains a blue exterior finish.'),
            lambda p:p.update(must_preserve=['red ceramic cup']),
            lambda p:p['candidate_edits'][0].update(object_description='null'),
            lambda p:p['candidate_edits'][0].update(unexpected='malformed'),
        )
        for number,change in enumerate(mutations):
            raw=deepcopy(self.raw);change(raw);case=self.build(raw)
            with self.subTest(number=number),self.assertRaises(ValueError):
                prepare(case,self.image,0,self.root/f'ineligible_{number}')

    def test_truncated_caption_is_ineligible(self):
        case=self.build(request=replace(self.request,caption_status=CaptionStatus.TRUNCATED))
        with self.assertRaises(ValueError):prepare(case,self.image,0,self.root/'truncated')

    def test_raw_review_and_abstain_are_ineligible(self):
        for decision in ('REVIEW','ABSTAIN'):
            raw={**self.raw,'decision':decision,'candidate_edits':[]};case=self.build(raw)
            with self.subTest(decision=decision),self.assertRaises(ValueError):
                prepare(case,self.image,0,self.root/decision)

    def test_unknown_extra_blocker_fails_closed(self):
        from transcreation.orchestration import validate_planner_audit
        audit=json.loads((self.case/'planner_audit.json').read_text())
        final,issues=validate_planner_audit(self.request,audit)
        issues.append({'code':'FUTURE_UNKNOWN_BLOCKER','message':'Synthetic unknown condition.', 'candidate_index':None,'severity':'review'})
        self.mutate(self.case/'planner_audit.json',lambda v:v['validation'].update(issues=issues))
        self.mutate(self.case/'validated_plan.json',lambda v:v.update(issues=issues))
        with patch('scripts.review_uncertainty.validate_planner_audit',return_value=(final,issues)),self.assertRaisesRegex(ValueError,'issue profile'):
            prepare(self.case,self.image,0,self.root/'unknown')

    def test_no_keyword_based_routine_classification(self):
        raw=deepcopy(self.raw);raw['uncertainties']=['A serious source-identity question remains unresolved.']
        pending=prepare(self.build(raw),self.image,0,self.root/'different_uncertainty')
        self.assertEqual(verify(pending)['decision'],'PENDING')
        self.assertFalse(verify(pending)['candidate_release_authorized'])

    def test_classification_cannot_be_consumed_as_edit_intent(self):
        from scripts.review_edit_intent import verify as verify_intent
        decision=self.classify()
        with self.assertRaises(ValueError):verify_intent(decision)
        request=PipelineInput(str(self.image),digest(self.image.read_bytes()),self.request.target_culture,
            str(self.root/'continuation'),'GROUNDING_TEST',user_instructions=self.request.user_instructions,
            verified_objects=self.request.verified_objects,edit_intent=IntentReference(str(decision),digest(decision.read_bytes())))
        result=run_pipeline(request)
        self.assertEqual(result.state,PipelineState.FAILED)
        self.assertFalse(result.image_generation_permitted)

    def test_audit_and_original_final_remain_byte_identical_after_classification(self):
        before={p.name:p.read_bytes() for p in self.case.iterdir()}
        bundle={p.name:p.read_bytes() for p in self.pending.parent.iterdir()}
        self.classify()
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.case.iterdir()})
        for name,data in bundle.items():self.assertEqual(data,(self.pending.parent/name).read_bytes())

    def test_permission_escalation_is_rejected(self):
        for field in PERMISSIONS:
            record=json.loads(self.pending.read_text());record[field]=True
            with self.subTest(field=field),self.assertRaises(ValueError):check(record,self.pending.parent)

    def test_changed_pending_request_invalidates_decision(self):
        decision=self.classify();self.pending.write_bytes(self.pending.read_bytes()+b' ')
        with self.assertRaises(ValueError):verify(decision)

    def test_existing_review_outputs_never_overwritten(self):
        decision=self.classify();before=decision.read_bytes()
        with self.assertRaises(FileExistsError):self.classify()
        self.assertEqual(before,decision.read_bytes())
        with self.assertRaises(FileExistsError):prepare(self.case,self.image,0,self.pending.parent)

    def test_changed_preview_or_readable_request_is_rejected(self):
        for filename in ('preview.png','review_request.md'):
            path=self.pending.parent/filename;before=path.read_bytes();path.write_bytes(before+b' ')
            with self.subTest(filename=filename),self.assertRaises(ValueError):verify(self.pending)
            path.write_bytes(before)

    def test_cli_displays_bound_instructions_uncertainties_and_no_permissions(self):
        with redirect_stdout(StringIO()) as output:main(['verify','--review',str(self.pending)])
        record=json.loads(output.getvalue())
        self.assertEqual(record['user_instructions'],self.request.user_instructions)
        self.assertEqual(record['original_uncertainties'],self.raw['uncertainties'])
        self.assertFalse(record['grounding_authorized'])

    def test_cli_classification_requires_all_inspection_declarations(self):
        out=self.pending.with_name('cli_decision.json')
        args=['decide','--pending',str(self.pending),'--out',str(out),'--decision','ROUTINE_VERIFICATION_REQUIRED',
              '--reviewer','synthetic reviewer','--reason','Synthetic assessment of normal pre-edit checks.']
        with redirect_stderr(StringIO()),self.assertRaises(SystemExit):main(args)
        self.assertFalse(out.exists())
        with redirect_stdout(StringIO()):main(args+['--'+flag.replace('_','-') for flag in DECLARATIONS])
        record=verify(out)
        self.assertEqual(record['decision'],'ROUTINE_VERIFICATION_REQUIRED')
        self.assertFalse(record['candidate_release_authorized'])

    def test_unknown_record_fields_or_decisions_rejected(self):
        record=json.loads(self.pending.read_text());record['candidate_edits']=[self.raw['candidate_edits'][0]]
        with self.assertRaises(ValueError):check(record,self.pending.parent)
        with self.assertRaises(ValueError):self.classify('ACCEPT_FOR_GROUNDING_TEST')

    def test_missing_evidence_rejected_before_preparation(self):
        (self.case/'raw_qwen_message.txt').unlink()
        with self.assertRaises(FileNotFoundError):prepare(self.case,self.image,0,self.root/'missing')

    def test_conflicting_raw_response_copies_rejected(self):
        self.mutate(self.case/'raw_response_before_validation.json',lambda v:v['message'].update(content='{}'))
        with self.assertRaises(ValueError):prepare(self.case,self.image,0,self.root/'conflict')

    def test_incomplete_wrong_model_or_nonassistant_responses_are_ineligible(self):
        changes=(lambda v:v.update(done=False),lambda v:v.update(done_reason='length'),
                 lambda v:v.update(model='unexpected-model'),lambda v:v['message'].update(role='system'),
                 lambda v:v['message'].update(tool_calls=[{'name':'not-an-edit-review'}]))
        for index,change in enumerate(changes):
            case=self.build()
            self.mutate(case/'planner_audit.json',lambda v:change(v['response']))
            self.mutate(case/'raw_response_before_validation.json',change)
            with self.subTest(index=index),self.assertRaisesRegex(ValueError,'incomplete or unexpected'):
                prepare(case,self.image,0,self.root/f'invalid_response_{index}')

    def test_duplicate_json_keys_rejected(self):
        self.pending.write_text(self.pending.read_text().replace('"decision": "PENDING"','"decision": "PENDING", "decision": "REJECT"'))
        with self.assertRaisesRegex(ValueError,'duplicate JSON key'):verify(self.pending)

    def test_cannot_erase_source_confirmation(self):
        self.mutate(self.case/'human_confirmation.json',lambda v:v.update(verbatim_user_confirmation=''))
        with self.assertRaises(ValueError):prepare(self.case,self.image,0,self.root/'erased')


if __name__=='__main__':
    unittest.main()

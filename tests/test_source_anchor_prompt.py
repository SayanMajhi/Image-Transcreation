"""Mocked Qwen responses test prompt delivery and safeguards, never real quality."""
from copy import deepcopy
from dataclasses import asdict
import json
import unittest
from unittest.mock import patch

from transcreation.config import PlannerConfig
from transcreation.contracts import CaptionStatus, PlanningInput, VerifiedObject
from transcreation.stages.ollama_planner import OllamaPlanner, SYSTEM_PROMPT, planning_result_schema


class SourceAnchorPromptTests(unittest.TestCase):
    def setUp(self):
        self.request=PlanningInput('An object is on a table.', CaptionStatus.COMPLETE, 'test target context',
            user_instructions='Change the exterior finish; preserve the table and lighting.',
            verified_objects=(VerifiedObject('item-1','red ceramic cup'),))
        self.raw={'decision':'PROPOSE','decision_reason':'Synthetic user-directed draft, not automatic approval.',
            'scene_summary':'The caption reports an object on a table; the user verified a red ceramic cup.',
            'candidate_edits':[{'object_description':'red ceramic cup','localization_phrase':'red ceramic cup',
                'proposed_change':'change the exterior to blue','cultural_reason':'Synthetic contextual user preference, not a cultural rule.',
                'identity_uncertain':False,'verified_object_id':'item-1'}],
            'must_preserve':['table','lighting'],'uncertainties':[],'verification_requirements':[]}

    def mocked_record(self, change=None):
        payload=deepcopy(self.raw)
        if change:change(payload)
        calls=[]
        def service(path, body=None, **kwargs):
            calls.append((path,deepcopy(body)))
            if path=='/api/tags':return {'models':[{'name':'qwen2.5:3b','digest':'SYNTHETIC_TEST_ONLY'}]}
            if body['messages']==[]:return {'done':True}
            return {'model':'qwen2.5:3b','done':True,'done_reason':'stop',
                    'message':{'role':'assistant','content':json.dumps(payload)}}
        planner=OllamaPlanner(PlannerConfig())
        with patch.object(planner,'api',side_effect=service):
            record=planner.record_plan(self.request)
        self.assertEqual(record['raw_planning_result'],payload)
        self.assertEqual(json.loads(record['response']['message']['content']),payload)
        return record,calls

    def test_read_only_anchor_and_attribution_rules_reach_actual_request(self):
        _,calls=self.mocked_record()
        body=next(body for path,body in calls if path=='/api/chat' and body['messages'])
        self.assertEqual(body['messages'][0]['content'],SYSTEM_PROMPT)
        self.assertIn('VERIFIED SOURCE IDENTITY IS READ-ONLY EVIDENCE.',body['messages'][0]['content'])
        self.assertIn("object_description must exactly copy that verified object's description",SYSTEM_PROMPT)
        self.assertIn('Never claim the caption said something it did not say.',SYSTEM_PROMPT)
        self.assertEqual(json.loads(body['messages'][1]['content']),json.loads(json.dumps(asdict(self.request))))

    def test_mock_valid_source_draft_keeps_schema_and_never_authorizes_edit(self):
        record,calls=self.mocked_record()
        body=next(body for path,body in calls if path=='/api/chat' and body['messages'])
        self.assertEqual(body['format'],planning_result_schema())
        self.assertEqual(record['planning_result']['decision'],'PROPOSE')
        self.assertFalse(record['validation']['automatically_authorized'])
        self.assertTrue(any('not approval' in text for text in record['planning_result']['verification_requirements']))

    def test_mock_future_source_description_is_rejected_without_repair(self):
        record,_=self.mocked_record(lambda p:p['candidate_edits'][0].update(
            object_description='blue ceramic cup',localization_phrase='blue ceramic cup',proposed_change='blue ceramic cup'))
        self.assertEqual(record['planning_result']['decision'],'REVIEW')
        self.assertEqual(record['planning_result']['candidate_edits'],())
        self.assertIn('SOURCE_OBJECT_MISMATCH',{i['code'] for i in record['validation']['issues']})
        self.assertEqual(record['validation']['rejected_candidates'][0]['raw_proposal']['object_description'],'blue ceramic cup')

    def test_mock_replacement_localization_cannot_release_candidate(self):
        record,_=self.mocked_record(lambda p:p['candidate_edits'][0].update(localization_phrase='blue exterior finish'))
        self.assertEqual(record['planning_result']['candidate_edits'],())
        self.assertIn('SOURCE_LOCALIZATION_MISMATCH',{i['code'] for i in record['validation']['issues']})

    def test_mock_review_and_abstain_are_never_promoted(self):
        for decision in ('REVIEW','ABSTAIN'):
            with self.subTest(decision=decision):
                record,_=self.mocked_record(lambda p:p.update(decision=decision,candidate_edits=[]))
                self.assertEqual(record['planning_result']['decision'],decision)
                self.assertEqual(record['planning_result']['candidate_edits'],())

    def test_mock_invented_verified_id_still_blocks(self):
        record,_=self.mocked_record(lambda p:p['candidate_edits'][0].update(verified_object_id='invented-id'))
        self.assertEqual(record['planning_result']['candidate_edits'],())
        self.assertIn('UNKNOWN_VERIFIED_OBJECT_ID',{i['code'] for i in record['validation']['issues']})


if __name__=='__main__':
    unittest.main()

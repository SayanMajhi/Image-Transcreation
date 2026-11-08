"""Offline SmolVLM chat-template and decoder-only contract checks."""
from contextlib import chdir, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
import torch

from transcreation.cli import main
from transcreation.config import CaptionConfig, load_config, validate_config
from transcreation.contracts import Captioner, CaptionTaskResult
from transcreation.pipeline import create_captioner
from transcreation.stages.caption import CONCISE_PROMPT, PROMPT, SmolVLMCaptioner
SHA = "a" * 40


def smol_config(**changes):
    return CaptionConfig(**{
        "active_model": "smolvlm", "model_id": "HuggingFaceTB/SmolVLM-500M-Instruct",
        "revision": SHA, "task": "caption", "device": "cpu", "num_beams": 1,
        "max_new_tokens": 128, **changes,
    })


class TestSmolVLM(unittest.TestCase):
    def mock_smol(self):
        processor = MagicMock()
        processor.tokenizer.init_kwargs = {"_commit_hash": SHA}
        processor.return_value = {
            "input_ids": torch.ones((1, 2), dtype=torch.long),
            "pixel_values": torch.ones((1, 3, 8, 8)),
            "attention_mask": torch.ones((1, 2), dtype=torch.long),
        }
        model = MagicMock()
        model.to.return_value = model
        model.config._commit_hash = SHA
        proc_cls, model_cls = MagicMock(), MagicMock()
        proc_cls.from_pretrained.return_value = processor
        model_cls.from_pretrained.return_value = model
        tf = SimpleNamespace(__version__="4.57.6", AutoProcessor=proc_cls)
        tf.AutoModelForImageTextToText = model_cls
        processor.apply_chat_template.return_value = "User:<image>fixed instruction Assistant:"
        processor.image_processor = SimpleNamespace(
            size={"longest_edge": 1024}, do_image_splitting=True, max_image_size={"longest_edge": 512},
        )
        processor.batch_decode.return_value = [" Two cats on a sofa. "]
        model.generation_config = SimpleNamespace(eos_token_id=2, pad_token_id=0)

        def generate(**kwargs):
            self.assertTrue(torch.is_inference_mode_enabled())
            self.assertFalse(torch.is_grad_enabled())
            self.assertFalse(kwargs["do_sample"])
            self.assertEqual(kwargs["input_ids"].dtype, torch.long)
            self.assertEqual(kwargs["pixel_values"].dtype, torch.float32)
            return torch.tensor([[101, 102, 20, 21, 2]])

        model.generate.side_effect = generate
        return tf, processor, model, proc_cls, model_cls

    def test_chat_template_loading_and_prompt_tokens_removed(self):
        tf, processor, model, proc_cls, model_cls = self.mock_smol()
        with patch("transcreation.stages.caption._transformers", return_value=tf):
            adapter = SmolVLMCaptioner(smol_config())
            self.assertIsInstance(adapter, Captioner)
            result = adapter.caption(Image.new("L", (32, 16)))
        self.assertEqual(result.caption, "Two cats on a sofa.")
        self.assertEqual(result.generated_tokens, 3)
        self.assertTrue(result.eos_reached)
        self.assertEqual(result.prompt_text, PROMPT)
        self.assertEqual(result.formatted_prompt, processor.apply_chat_template.return_value)
        messages = processor.apply_chat_template.call_args.args[0]
        self.assertEqual(messages, [{"role": "user", "content": [
            {"type": "image"}, {"type": "text", "text": PROMPT},
        ]}])
        self.assertEqual(processor.apply_chat_template.call_args.kwargs,
                         {"tokenize": False, "add_generation_prompt": True})
        self.assertEqual(processor.batch_decode.call_args.args[0].tolist(), [[20, 21, 2]])
        self.assertEqual(processor.call_args.kwargs["images"][0].mode, "RGB")
        proc_cls.from_pretrained.assert_called_once()
        self.assertEqual(proc_cls.from_pretrained.call_args.kwargs["size"], {"longest_edge": 1024})
        model_cls.from_pretrained.assert_called_once()
        self.assertFalse(model_cls.from_pretrained.call_args.kwargs["trust_remote_code"])
        self.assertEqual(model_cls.from_pretrained.call_args.kwargs["attn_implementation"], "sdpa")
        model.generate.assert_called_once()

    def test_config_factory_and_no_other_model_construction(self):
        selected = load_config(Path("configs/models.yaml"), model="smolvlm")
        self.assertEqual(selected.num_beams, 1)
        self.assertEqual(selected.max_new_tokens, 128)
        with patch("transcreation.stages.caption.SmolVLMCaptioner") as smol:
            self.assertIs(create_captioner(smol_config()), smol.return_value)
        smol.assert_called_once_with(smol_config())

    def test_cli_serializes_prompt_metadata_and_measurements(self):
        tf, _, _, _, _ = self.mock_smol()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "source.png"
            Image.new("RGB", (32, 16)).save(image)
            output = root / "smol.json"
            with patch("transcreation.config.load_config", return_value=smol_config()), \
                 patch("transcreation.stages.caption._transformers", return_value=tf), \
                 redirect_stdout(StringIO()):
                main(["caption", "--image", str(image), "--model", "smolvlm", "--out", str(output)])
            record = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(record["prompt_text"], PROMPT)
            self.assertEqual(record["image_dimensions"], [32, 16])
            self.assertGreaterEqual(record["inference_ms"], 0)
            self.assertIsNone(record["peak_gpu_memory_bytes"])
            self.assertEqual(record["precision"], "float32")

    def test_empty_caption_is_rejected(self):
        tf, processor, _, _, _ = self.mock_smol()
        processor.batch_decode.return_value = [" "]
        with patch("transcreation.stages.caption._transformers", return_value=tf):
            adapter = SmolVLMCaptioner(smol_config())
            with self.assertRaisesRegex(ValueError, "empty caption"):
                adapter.caption(Image.new("RGB", (8, 8)))

    def test_concise_prompt_and_truncation_metadata(self):
        tf, _, model, _, _ = self.mock_smol()
        model.generate.side_effect = None
        model.generate.return_value = torch.tensor([[101, 102, 20, 21, 22]])
        with patch("transcreation.stages.caption._transformers", return_value=tf):
            result = SmolVLMCaptioner(smol_config(
                prompt_variant="concise_grounded", max_new_tokens=3,
            )).caption(Image.new("RGB", (8, 8)))
        self.assertEqual(result.prompt_text, CONCISE_PROMPT)
        self.assertEqual(result.prompt_variant, "concise_grounded")
        self.assertFalse(result.eos_reached)
        self.assertTrue(result.token_ceiling_reached)
        self.assertEqual(result.generated_tokens, 3)


class TestApplication(unittest.TestCase):
    def test_cli_finds_default_settings_outside_project_folder(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "source.png"
            output = root / "caption.json"
            Image.new("RGB", (8, 8)).save(image)
            result = CaptionTaskResult(
                caption="A test image.", model_id="HuggingFaceTB/SmolVLM-500M-Instruct",
            )
            with chdir(root), \
                 patch("transcreation.pipeline.create_captioner") as factory, \
                 redirect_stdout(StringIO()):
                factory.return_value.caption.return_value = result
                main(["caption", "--image", str(image), "--out", str(output)])
            self.assertEqual(factory.call_args.args[0].active_model, "smolvlm")
            self.assertEqual(json.loads(output.read_text())["caption"], "A test image.")

    def test_default_config_selects_pinned_smolvlm(self):
        selected = load_config(Path("configs/models.yaml"))
        self.assertEqual(selected.active_model, "smolvlm")
        self.assertEqual(selected.model_id, "HuggingFaceTB/SmolVLM-500M-Instruct")
        self.assertEqual(selected.revision, "a7da5b986cb59b408707209984f360a5f4ad7e47")
        self.assertTrue(selected.generation_settings()["use_cache"])

    def test_retired_models_and_commands_are_rejected(self):
        for name in ("blip", "florence"):
            with self.subTest(model=name), self.assertRaises(ValueError):
                validate_config({"models": {"smolvlm": {}}}, model=name)
            with self.subTest(cli=name), patch("sys.stderr", new_callable=StringIO), \
                 self.assertRaises(SystemExit) as exc:
                main(["caption", "--image", "unused.png", "--model", name])
            self.assertEqual(exc.exception.code, 2)
        with patch("sys.stderr", new_callable=StringIO), self.assertRaises(SystemExit) as exc:
            main(["compare-vlms"])
        self.assertEqual(exc.exception.code, 2)

    def test_invalid_settings_are_rejected(self):
        for change in ({"max_new_tokens": 0}, {"num_beams": True}, {"seed": -1},
                       {"task": "<CAPTION>"}, {"model_id": "other/checkpoint"},
                       {"prompt_variant": "unknown"}, {"device": "invalid"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                smol_config(**change)
        with self.assertRaisesRegex(ValueError, "Unknown settings"):
            validate_config({"models": {"smolvlm": {"allow_remote_code": True}}})

    def test_cpu_precision_fallback_and_unavailable_cuda(self):
        with patch("torch.cuda.is_available", return_value=False), \
             patch("transcreation.stages.caption.SmolVLMCaptioner") as adapter:
            with self.assertWarns(RuntimeWarning):
                create_captioner(smol_config(device="auto", precision="float16"))
            resolved = adapter.call_args.args[0]
            self.assertEqual((resolved.device, resolved.precision), ("cpu", "float32"))
            with self.assertRaisesRegex(RuntimeError, "CUDA requested but unavailable"):
                create_captioner(smol_config(device="cuda"))

    def test_cli_refuses_to_overwrite_source_image(self):
        with TemporaryDirectory() as directory:
            image = Path(directory) / "source.png"
            Image.new("RGB", (8, 8)).save(image)
            original = image.read_bytes()
            with patch("transcreation.pipeline.create_captioner") as factory, \
                 patch("sys.stderr", new_callable=StringIO), self.assertRaises(SystemExit):
                main(["caption", "--image", str(image), "--out", str(image)])
            factory.assert_not_called()
            self.assertEqual(image.read_bytes(), original)

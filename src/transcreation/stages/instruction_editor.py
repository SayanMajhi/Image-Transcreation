"""Isolated research instruction editors; existing SD1.5 implementation stays unchanged.

FLUX conditions on RGB, not a native mask. Locality comes from the existing compositor.
SDXL uses a separate, source-bound ControlNet image. Neither route consumes planner drafts.
"""
from dataclasses import asdict, dataclass
import gc
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace

import numpy as np
from PIL import Image

from transcreation.config import InpaintingConfig
from transcreation.contracts import InpaintingInput
from transcreation.stages.inpainting import prepare_crop, restore_and_composite, validate_mask

PINS = {
    'FLUX_KONTEXT_GGUF': ('black-forest-labs/FLUX.1-Kontext-dev', '24e9dedc4ef646698dc8eb4e18ae2cec3c9fea0d'),
    'SDXL_CONTROLNET_CANNY': ('diffusers/stable-diffusion-xl-1.0-inpainting-0.1', '115134f363124c53c7d878647567d04daf26e41e'),
}
CONTROL_PIN = ('diffusers/controlnet-canny-sdxl-1.0','eb115a19a10d14909256db740ed109532ab1483c')
GGUF_SHA256 = 'ebd4e92c44c47f104ad64e4353692f37addf06eb99420c9b459334d871c8b750'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''): h.update(block)
    return h.hexdigest()


@dataclass(frozen=True)
class InstructionEditInput:
    source_image: str
    source_sha256: str
    specification_file: str
    specification_sha256: str
    mask_file: str
    mask_sha256: str
    protected_file: str
    protected_sha256: str
    crop_box: tuple[int, int, int, int]
    prompt: str
    seed: int
    scope: str = 'RESEARCH_ONLY'
    control_file: str | None = None
    control_sha256: str | None = None

    def __post_init__(self):
        if self.scope != 'RESEARCH_ONLY': raise ValueError('no automated or approved execution in this research route')
        if not isinstance(self.prompt,str) or not self.prompt.strip(): raise ValueError('explicit edit prompt required')
        if type(self.seed) is not int or not 0 <= self.seed < 2**32: raise ValueError('explicit uint32 seed required')
        if len(self.crop_box)!=4 or any(type(x) is not int for x in self.crop_box): raise ValueError('integer XYXY crop required')
        for name in ('source_sha256','specification_sha256','mask_sha256','protected_sha256'):
            h=getattr(self,name)
            if not isinstance(h,str) or len(h)!=64 or any(x not in '0123456789abcdef' for x in h):
                raise ValueError('SHA-256 required: '+name)
        if (self.control_file is None)!=(self.control_sha256 is None): raise ValueError('control image and hash must be paired')


def validate_edit(request, config):
    if type(request) is not InstructionEditInput: raise ValueError('independent research specification required, not a planner/review record')
    if config.get('backend') not in PINS or (config.get('model_id'),config.get('revision'))!=PINS[config['backend']]:
        raise ValueError('unrecognized backend or unpinned model')
    if config['backend']=='SDXL_CONTROLNET_CANNY' and (config.get('controlnet_id'),config.get('controlnet_revision'))!=CONTROL_PIN:
        raise ValueError('ControlNet identity must match declared structural fallback')
    if (type(config.get('processing_size')) is not int or not 64<=config['processing_size']<=1024
            or config['processing_size']%64 or type(config.get('context_margin')) is not int
            or config['context_margin']<0 or type(config.get('steps')) is not int or not 1<=config['steps']<=100):
        raise ValueError('invalid processing geometry or step budget')
    for path,h in [(request.source_image,request.source_sha256),(request.mask_file,request.mask_sha256),
                   (request.protected_file,request.protected_sha256),(request.specification_file,request.specification_sha256)]:
        if sha(path)!=h: raise ValueError('source-bound evidence SHA-256 mismatch: '+str(path))
    spec=json.loads(Path(request.specification_file).read_text())
    if spec.get('scope')!='RESEARCH_ONLY' or spec.get('human_approved') is not False or spec.get('source_image_sha256')!=request.source_sha256:
        raise ValueError('research specification must bind source and must not claim human approval')
    for name in ('source_object','target_object','must_preserve','visual_requirements'):
        if not spec.get(name): raise ValueError('incomplete research edit specification: '+name)
    with Image.open(request.source_image) as im: image=im.convert('RGB')
    with Image.open(request.mask_file) as im: mask=im.copy()
    with Image.open(request.protected_file) as im: protected=im.copy()
    validate_mask(image,mask); validate_mask(image,protected)
    if np.any((np.asarray(mask)==255)&(np.asarray(protected)==255)): raise ValueError('protected/edit region conflict')
    # Shared geometry utility only needs these two attributes; do not relax SD1.5's fixed-size contract.
    crop_config=SimpleNamespace(processing_size=config['processing_size'],context_margin=config['context_margin'])
    working,working_mask,geometry=prepare_crop(image,mask,crop_config)
    if tuple(geometry['crop_box_xyxy'])!=tuple(request.crop_box): raise ValueError('declared crop does not match source mask mapping')
    control=None
    if config['backend']=='SDXL_CONTROLNET_CANNY':
        if request.control_file is None or sha(request.control_file)!=request.control_sha256: raise ValueError('pinned control condition required')
        with Image.open(request.control_file) as im:
            if im.mode!='RGB' or im.size!=image.size: raise ValueError('control coordinates must match original RGB image')
            control,_,control_geometry=prepare_crop(im,mask,crop_config)
        if control_geometry!=geometry: raise ValueError('control/source transforms disagree')
    return image,mask,protected,working,working_mask,geometry,control


def load_editor(config):
    """Offline-only load: prefetch explicitly with recorded repository revisions/checksums."""
    import torch
    from huggingface_hub import snapshot_download
    folder=snapshot_download(config['model_id'],revision=config['revision'],local_files_only=True)
    if Path(folder).name!=config['revision']: raise ValueError('model revision mismatch')
    if config['backend']=='SDXL_CONTROLNET_CANNY':
        from diffusers import ControlNetModel, StableDiffusionXLControlNetInpaintPipeline
        control_folder=snapshot_download(config['controlnet_id'],revision=config['controlnet_revision'],local_files_only=True)
        if Path(control_folder).name!=config['controlnet_revision']: raise ValueError('ControlNet revision mismatch')
        control=ControlNetModel.from_pretrained(control_folder,torch_dtype=torch.float16,variant='fp16',use_safetensors=True,local_files_only=True)
        pipe=StableDiffusionXLControlNetInpaintPipeline.from_pretrained(folder,controlnet=control,
            torch_dtype=torch.float16,variant='fp16',use_safetensors=True,local_files_only=True)
    else:
        from diffusers import FluxKontextPipeline, FluxTransformer2DModel, GGUFQuantizationConfig
        if (config.get('quantization')!='Q4_K_M' or config.get('gguf_sha256')!=GGUF_SHA256
                or sha(config['gguf_file'])!=GGUF_SHA256):
            raise ValueError('explicit verified Q4_K_M transformer required')
        transformer=FluxTransformer2DModel.from_single_file(config['gguf_file'],config=folder,subfolder='transformer',
            quantization_config=GGUFQuantizationConfig(compute_dtype=torch.float16),torch_dtype=torch.float16,local_files_only=True)
        pipe=FluxKontextPipeline.from_pretrained(folder,transformer=transformer,torch_dtype=torch.float16,use_safetensors=True,local_files_only=True)
    pipe.enable_sequential_cpu_offload()
    pipe.enable_attention_slicing('max')
    pipe.enable_vae_tiling()
    return pipe


def run_editor(request,config,out):
    # Preserve the original SD1.5 entry point/contracts as a baseline, without reimplementation.
    if type(request) is InpaintingInput and type(config) is InpaintingConfig:
        from transcreation.stages.inpainting import run_inpainting
        return run_inpainting(request,config,Path(out))
    started=time.perf_counter()
    image,mask,protected,working,working_mask,geometry,control=validate_edit(request,config)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    report={'status':'FAILED','scope':'RESEARCH_ONLY','human_approved':False,'automated_edit_authorized':False,
        'request':asdict(request),'backend':config['backend'],'model_config':config,'geometry':geometry,
        'native_binary_mask_support':config['backend']=='SDXL_CONTROLNET_CANNY','calls_attempted':0}
    def save(): (out/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save();working.save(out/'processing_source.png');working_mask.save(out/'processing_mask.png')
    if control is not None:control.save(out/'processing_control.png')
    pipe=None
    try:
        import torch
        if not torch.cuda.is_available():raise RuntimeError('CUDA required for this bounded feasibility run')
        torch.cuda.reset_peak_memory_stats();tick=time.perf_counter();pipe=load_editor(config)
        report['load_seconds']=time.perf_counter()-tick
        report['actual_scheduler']=type(pipe.scheduler).__name__ if hasattr(pipe,'scheduler') else None
        for tokenizer in [getattr(pipe,'tokenizer',None),getattr(pipe,'tokenizer_2',None)]:
            if tokenizer is not None and config['backend']=='SDXL_CONTROLNET_CANNY':
                if len(tokenizer(request.prompt).input_ids)>tokenizer.model_max_length:raise ValueError('prompt exceeds tokenizer context')
        kwargs=dict(image=working,prompt=request.prompt,width=working.width,height=working.height,
            generator=torch.Generator(device='cpu').manual_seed(request.seed),num_inference_steps=config['steps'],
            guidance_scale=config['guidance_scale'])
        if control is not None:kwargs.update(mask_image=working_mask,control_image=control,strength=config['strength'],
            controlnet_conditioning_scale=config['control_scale'],negative_prompt=config['negative_prompt'])
        report['calls_attempted']=1;save();tick=time.perf_counter()
        with torch.inference_mode():raw=pipe(**kwargs).images[0].convert('RGB')
        torch.cuda.synchronize();report['inference_seconds']=time.perf_counter()-tick
        report['effective_denoising_steps']=getattr(pipe,'num_timesteps',None)
        report['peak_cuda_allocated_bytes']=torch.cuda.max_memory_allocated()
        raw.save(out/'raw.png')
        final,restored,_,metrics=restore_and_composite(image,mask,raw,geometry)
        final.save(out/'final.png');restored.save(out/'restored.png')
        # Independently reopen the saved PNG, rather than trusting only the compositor metrics.
        with Image.open(out/'final.png') as im:
            if im.mode!='RGB' or im.size!=image.size:raise ValueError('saved image contract failed')
            delta=np.any(np.asarray(im)!=np.asarray(image),axis=2)
        metrics.update(changed_in_protected_regions=int((delta&(np.asarray(protected)==255)).sum()))
        if delta[np.asarray(mask)==0].any() or metrics['changed_in_protected_regions']:raise ValueError('saved output locality failed')
        if not metrics['changed_inside_mask']:raise ValueError('no actual editable pixel change')
        report.update(status='COMPLETED',metrics=metrics,output_sha256=sha(out/'final.png'))
    except Exception as exc:
        report['error']={'type':type(exc).__name__,'message':str(exc)}
        raise
    finally:
        if pipe is not None:
            try:
                if hasattr(pipe,'maybe_free_model_hooks'):pipe.maybe_free_model_hooks()
            except Exception as cleanup_error:
                report['cleanup_warning']=str(cleanup_error)
            del pipe
        gc.collect()
        import torch
        if torch.cuda.is_available():torch.cuda.empty_cache()
        report['process_seconds']=time.perf_counter()-started;save()
    return report

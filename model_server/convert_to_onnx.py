import torch
import torch.onnx
import argparse
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_pytorch_to_onnx(pytorch_model_path: str, onnx_output_path: str, input_size: int = 10):
    logger.info(f"Loading PyTorch model from {pytorch_model_path}")
    
    if pytorch_model_path.endswith('.pt') or pytorch_model_path.endswith('.pth'):
        model = torch.load(pytorch_model_path, map_location='cpu')
        
        if isinstance(model, dict) and 'model' in model:
            model = model['model']
    else:
        model = torch.jit.load(pytorch_model_path, map_location='cpu')
    
    model.eval()
    
    dummy_input = torch.randn(1, input_size)
    
    logger.info(f"Converting to ONNX format: {onnx_output_path}")
    
    torch.onnx.export(
        model,
        dummy_input,
        onnx_output_path,
        export_params=True,
        opset_version=11,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )
    
    logger.info("Conversion completed successfully")
    
    import onnxruntime as ort
    
    session = ort.InferenceSession(onnx_output_path, providers=['CPUExecutionProvider'])
    
    test_input = dummy_input.numpy()
    ort_inputs = {session.get_inputs()[0].name: test_input}
    ort_outputs = session.run(None, ort_inputs)
    
    logger.info("ONNX model validated successfully")
    logger.info(f"Output shape: {ort_outputs[0].shape}")
    
    original_size = os.path.getsize(pytorch_model_path) / (1024 * 1024)
    onnx_size = os.path.getsize(onnx_output_path) / (1024 * 1024)
    
    logger.info(f"Original model size: {original_size:.2f} MB")
    logger.info(f"ONNX model size: {onnx_size:.2f} MB")
    logger.info(f"Size reduction: {((original_size - onnx_size) / original_size * 100):.1f}%")


def convert_to_torchscript(pytorch_model_path: str, torchscript_output_path: str, input_size: int = 10):
    logger.info(f"Loading PyTorch model from {pytorch_model_path}")
    
    model = torch.load(pytorch_model_path, map_location='cpu')
    
    if isinstance(model, dict) and 'model' in model:
        model = model['model']
    
    model.eval()
    
    dummy_input = torch.randn(1, input_size)
    
    logger.info(f"Converting to TorchScript: {torchscript_output_path}")
    
    traced_model = torch.jit.trace(model, dummy_input)
    
    torch.jit.save(traced_model, torchscript_output_path)
    
    logger.info("TorchScript conversion completed successfully")
    
    loaded_model = torch.jit.load(torchscript_output_path)
    test_output = loaded_model(dummy_input)
    
    logger.info("TorchScript model validated successfully")
    logger.info(f"Output shape: {test_output.shape}")


def main():
    parser = argparse.ArgumentParser(description='Convert PyTorch models to ONNX or TorchScript')
    parser.add_argument('input', type=str, help='Input PyTorch model path (.pt, .pth, or TorchScript)')
    parser.add_argument('output', type=str, help='Output model path (.onnx or .pt for TorchScript)')
    parser.add_argument('--input-size', type=int, default=10, help='Input feature size (default: 10)')
    parser.add_argument('--format', type=str, choices=['onnx', 'torchscript'], default='onnx',
                        help='Output format (default: onnx)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        return
    
    try:
        if args.format == 'onnx':
            convert_pytorch_to_onnx(args.input, args.output, args.input_size)
        else:
            convert_to_torchscript(args.input, args.output, args.input_size)
        
        logger.info("Conversion completed successfully")
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()

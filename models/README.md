# detect.tflite

SSD-style model (class/score/count output tensors). Labels in `coco_labels.txt` (person is index 0).

## Download

From the repo root on the Pi:

```bash
curl -L -o models/detect.tflite \
  https://github.com/google-coral/test_data/raw/master/ssdlite_mobilenet_v2_coco_quant_postprocess.tflite
```

## Check

```bash
ls -la models/detect.tflite
```

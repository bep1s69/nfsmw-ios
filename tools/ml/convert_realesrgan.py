#!/usr/bin/env python3
"""Real-ESRGAN x4 (anime 6B, BSD-3, xinntao/Real-ESRGAN v0.2.2.4) to Core ML.

The app upscales its HUD textures 4x once with it (native_renderer.mm, sharp
HUD). Run with the converter venv:
  ~/Library/Caches/nfsmw-ios/ml-venv/bin/python tools/ml/convert_realesrgan.py \
      ~/Library/Caches/nfsmw-ios/ml-model/RealESRGAN_x4plus_anime_6B.pth ios/resources/HudUpscale.mlpackage
Input "image" [1,3,H,W] float16 RGB 0..1 (H, W in 32..512, powers of two);
output "upscaled" [1,3,4H,4W].
"""
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import coremltools as ct


class ResidualDenseBlock(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, nf, gc=32):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(nf, gc)
        self.rdb2 = ResidualDenseBlock(nf, gc)
        self.rdb3 = ResidualDenseBlock(nf, gc)

    def forward(self, x):
        out = self.rdb3(self.rdb2(self.rdb1(x)))
        return out * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(self, num_block=6, nf=64, gc=32):
        super().__init__()
        self.conv_first = nn.Conv2d(3, nf, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(nf, gc) for _ in range(num_block)])
        self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        feat = self.conv_first(x)
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
        return torch.clamp(self.conv_last(self.lrelu(self.conv_hr(feat))), 0.0, 1.0)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    net = RRDBNet()
    state = torch.load(src, map_location="cpu", weights_only=True)
    state = state.get("params_ema", state.get("params", state))
    net.load_state_dict(state, strict=True)
    net.eval()
    example = torch.rand(1, 3, 64, 64)
    traced = torch.jit.trace(net, example)
    sizes = [32, 64, 128, 256, 512]
    shapes = ct.EnumeratedShapes(shapes=[[1, 3, h, w] for h in sizes for w in sizes], default=[1, 3, 64, 64])
    model = ct.convert(traced, inputs=[ct.TensorType(name="image", shape=shapes)],
                       outputs=[ct.TensorType(name="upscaled")],
                       compute_precision=ct.precision.FLOAT16, minimum_deployment_target=ct.target.iOS17,
                       convert_to="mlprogram")
    model.short_description = "Real-ESRGAN x4 anime 6B (BSD-3, xinntao/Real-ESRGAN) for HUD textures"
    model.save(dst)
    # Quick check: an edge stays an edge.
    import numpy as np
    x = np.zeros((1, 3, 32, 32), np.float32)
    x[:, :, :, 16:] = 1
    y = model.predict({"image": x})["upscaled"]
    print("ok", y.shape, float(y[0, 0, 64, 60]), float(y[0, 0, 64, 68]))


main()

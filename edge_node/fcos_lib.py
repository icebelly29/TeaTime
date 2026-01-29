#!/usr/bin/env python3

import sys
import os
import ctypes
import json
import numpy as np
import cv2

# Define C structures matching the library
class hbSysMem_t(ctypes.Structure):
    _fields_ = [
        ("phyAddr",ctypes.c_double),
        ("virAddr",ctypes.c_void_p),
        ("memSize",ctypes.c_int)
    ]

class hbDNNQuantiShift_yt(ctypes.Structure):
    _fields_ = [
        ("shiftLen",ctypes.c_int),
        ("shiftData",ctypes.c_char_p)
    ]

class hbDNNQuantiScale_t(ctypes.Structure):
    _fields_ = [
        ("scaleLen",ctypes.c_int),
        ("scaleData",ctypes.POINTER(ctypes.c_float)),
        ("zeroPointLen",ctypes.c_int),
        ("zeroPointData",ctypes.c_char_p)
    ]

class hbDNNTensorShape_t(ctypes.Structure):
    _fields_ = [
        ("dimensionSize",ctypes.c_int * 8),
        ("numDimensions",ctypes.c_int)
    ]

class hbDNNTensorProperties_t(ctypes.Structure):
    _fields_ = [
        ("validShape",hbDNNTensorShape_t),
        ("alignedShape",hbDNNTensorShape_t),
        ("tensorLayout",ctypes.c_int),
        ("tensorType",ctypes.c_int),
        ("shift",hbDNNQuantiShift_yt),
        ("scale",hbDNNQuantiScale_t),
        ("quantiType",ctypes.c_int),
        ("quantizeAxis", ctypes.c_int),
        ("alignedByteSize",ctypes.c_int),
        ("stride",ctypes.c_int * 8)
    ]

class hbDNNTensor_t(ctypes.Structure):
    _fields_ = [
        ("sysMem",hbSysMem_t * 4),
        ("properties",hbDNNTensorProperties_t)
    ]

class FcosPostProcessInfo_t(ctypes.Structure):
    _fields_ = [
        ("height",ctypes.c_int),
        ("width",ctypes.c_int),
        ("ori_height",ctypes.c_int),
        ("ori_width",ctypes.c_int),
        ("score_threshold",ctypes.c_float),
        ("nms_threshold",ctypes.c_float),
        ("nms_top_k",ctypes.c_int),
        ("is_pad_resize",ctypes.c_int)
    ]

# Load shared library
try:
    libpostprocess = ctypes.CDLL('/usr/lib/libpostprocess.so')
    get_Postprocess_result = libpostprocess.FcosPostProcess
    get_Postprocess_result.argtypes = [ctypes.POINTER(FcosPostProcessInfo_t)]
    get_Postprocess_result.restype = ctypes.c_char_p
except OSError:
    print("[WARN] libpostprocess.so not found. FCOS post-processing will fail.")
    libpostprocess = None

def get_TensorLayout(Layout):
    if Layout == "NCHW":
        return int(2)
    else:
        return int(0)

class FcosPostProcessor:
    def __init__(self, model_outputs, input_w=512, input_h=512, ori_w=1920, ori_h=1080):
        if libpostprocess is None:
            raise ImportError("libpostprocess.so not loaded")

        self.info = FcosPostProcessInfo_t()
        self.info.height = input_h
        self.info.width = input_w
        self.info.ori_height = ori_h
        self.info.ori_width = ori_w
        self.info.score_threshold = 0.5
        self.info.nms_threshold = 0.6
        self.info.nms_top_k = 5
        self.info.is_pad_resize = 0

        self.output_tensors = (hbDNNTensor_t * len(model_outputs))()

        for i in range(len(model_outputs)):
            self.output_tensors[i].properties.tensorLayout = get_TensorLayout(model_outputs[i].properties.layout)
            
            if (len(model_outputs[i].properties.scale_data) == 0):
                self.output_tensors[i].properties.quantiType = 0
            else:
                self.output_tensors[i].properties.quantiType = 2
                scale_data_tmp = model_outputs[i].properties.scale_data.reshape(1, 1, 1, model_outputs[i].properties.shape[3])
                self.output_tensors[i].properties.scale.scaleData = scale_data_tmp.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

            for j in range(len(model_outputs[i].properties.shape)):
                self.output_tensors[i].properties.validShape.dimensionSize[j] = model_outputs[i].properties.shape[j]
                self.output_tensors[i].properties.alignedShape.dimensionSize[j] = model_outputs[i].properties.shape[j]

    def process(self, outputs):
        strides = [8, 16, 32, 64, 128]
        # Ensure we don't go out of bounds if model output count differs
        num_strides = min(len(strides), len(outputs) // 3)
        
        for i in range(num_strides):
            if (self.output_tensors[i].properties.quantiType == 0):
                self.output_tensors[i].sysMem[0].virAddr = ctypes.cast(outputs[i].buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ctypes.c_void_p)
                self.output_tensors[i + 5].sysMem[0].virAddr = ctypes.cast(outputs[i + 5].buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ctypes.c_void_p)
                self.output_tensors[i + 10].sysMem[0].virAddr = ctypes.cast(outputs[i + 10].buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ctypes.c_void_p)
            else:
                self.output_tensors[i].sysMem[0].virAddr = ctypes.cast(outputs[i].buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)), ctypes.c_void_p)
                self.output_tensors[i + 5].sysMem[0].virAddr = ctypes.cast(outputs[i + 5].buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)), ctypes.c_void_p)
                self.output_tensors[i + 10].sysMem[0].virAddr = ctypes.cast(outputs[i + 10].buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)), ctypes.c_void_p)

            libpostprocess.FcosdoProcess(self.output_tensors[i], self.output_tensors[i + 5], self.output_tensors[i + 10], ctypes.pointer(self.info), i)

        result_str = get_Postprocess_result(ctypes.pointer(self.info))
        result_str = result_str.decode('utf-8')
        
        # result_str is usually "post_process_result: JSON_DATA"
        # We need to strip the prefix
        try:
            # Assuming format: "post_process_result: [...]" or just json
            if "post_process_result:" in result_str:
                json_str = result_str.split("post_process_result:")[1].strip()
            else:
                json_str = result_str
            
            if not json_str:
                return []
                
            return json.loads(json_str)
        except Exception as e:
            print(f"[ERROR] Failed to parse FCOS result: {e}")
            return []
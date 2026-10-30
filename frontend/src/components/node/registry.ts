import triggerDefinition from "./trigger/trigger-node.ts";
import outboundsFctDefinition from "./function/outbounds-fct-node.ts";
import minWindowFctDefinition from "./windows/min-window-fct-node.ts";
import slidingAmpGradientDefinition from "./visual/sliding-amp-gradient-node.ts";
import differenceDefinition from "./transforms/difference-node.ts";
import esp32Definition from "./controllers/esp32-node.ts";
import kickDecayDefinition from "./groups/kick-decay-node.ts";
import snareDecayDefinition from "./groups/snare-decay-node.ts";
import singlePeakTriggerDefinition from "./groups/single-peak-trigger-node.ts";
import edgeToCenterTriggerDefinition from "./groups/edge-to-center-trigger-node.ts";
import centerToEdgeDefinition from "./groups/center-to-edge-node.ts";
import bufferDefinition from "./buffer/buffer-node.ts";
import groupDefinition from "./groups/group-node.ts";
import routingDefinition from "./routing/routing-node.ts";
import gatheringDefinition from "./routing/gathering-node.ts";
import constantArrayDefinition from "./simple/constant-array-node.ts";
import functionDefinition from "./function/function-node.ts";
import singleColorDefinition from "./visual/single-color-node.ts";
import sinArrayDefinition from "./simple/sin-array-node.ts";
import amplitudesDefinition from "./amplitudes/amplitudes-node.ts";
import smoothingDefinition from "./transforms/smoothing-node.ts";
import lowFilterDefinition from "./auditory/low-filter-node.ts";
import highFilterDefinition from "./auditory/high-filter-node.ts";
import bandFilterDefinition from "./auditory/band-filter-node.ts";
import rmsDefinition from "./auditory/rms-node.ts";
import midSideEnergyDefinition from "./features/mid-side-energy-node.ts";
import zeroCrossingRateDefinition from "./features/zero-crossing-rate-node.ts";
import crestFactorDefinition from "./features/crest-factor-node.ts";
import entropyDefinition from "./features/entropy-node.ts";
import spectralFluxDefinition from "./features/spectral-flux-node.ts";
import onsetStrengthDefinition from "./features/onset-strength-node.ts";
import spectralCentroidDefinition from "./features/spectral-centroid-node.ts";
import pitchClassChromaDefinition from "./features/pitch-class-chroma-node.ts";
import chromaPrismDefinition from "./features/chroma-prism-node.ts";
import windowDefinition from "./window/window-node.ts";
import averagedWindowFctDefinition from "./windows/averaged-window-fct-node.ts";
import ceilWindowFctDefinition from "./windows/ceil-window-fct-node.ts";
import decreasingAvgWindowFctDefinition from "./windows/decreasing-avg-window-fct-node.ts";
import maxWindowFctDefinition from "./windows/max-window-fct-node.ts";
import sumWindowFctDefinition from "./windows/sum-window-fct-node.ts";
import barGraphChartDefinition from "./visual/bar-graph-chart-node.ts";
import multiLineChartDefinition from "./visual/multi-line-chart-node.ts";
import singleLineChartDefinition from "./visual/single-line-chart-node.ts";
import rainbowDefinition from "./rainbow/rainbow-node.ts";
import gradiantDefinition from "./rainbow/gradiant-node.ts";
import broadcastAdditionDefinition from "./broadcast/broadcast-addition-node.ts";
import rollingDefinition from "./visual/rolling-node.ts";
import valueTransformerDefinition from "./transforms/value-transformer-node.ts";
import operatorPipelineDefinition from "./transforms/operator-pipeline-node.ts";
import clipDefinition from "./transforms/clip-node.ts";
import peakFilterDefinition from "./transforms/peak-filter-node.ts";
import thresholdFilterDefinition from "./transforms/threshold-filter-node.ts";
import avgFrequenciesDefinition from "./amplitudes/avg-frequencies-node.ts";
import linearAmplitudesTransformerDefinition from "./amplitudes/linear-amplitudes-transformer-node.ts";
import freqScaledAmplitudesTransformerDefinition from "./amplitudes/freq-scaled-amplitudes-transformer-node.ts";
import fctAmplitudesTransformerDefinition from "./amplitudes/fct-amplitudes-transformer-node.ts";
import amplitudeLevelFunctionDefinition from "./amplitudes/amplitude-level-function-node.ts";
import streamPlayerDefinition from "./stream/stream-player-node.ts";
import streamMicDefinition from "./stream/stream-mic-node.ts";
import soundcloudPlayerDefinition from "./player/soundcloud-player-node.ts";
import stemsRecognitionDefinition from "./offline/stems-recognition-node.ts";
import rgbapipelineDefinition from "./visual/rgbapipeline-node.ts";
import broadcastFractionDefinition from "./broadcast/broadcast-fraction-node.ts";
import broadcastIndexesDefinition from "./broadcast/broadcast-indexes-node.ts";
import broadcastRescalerDefinition from "./broadcast/broadcast-rescaler-node.ts";
import type { NodeDefinition } from "./definition.ts";

export const nodeDefinitions: Record<string, NodeDefinition> = {
  "Trigger": triggerDefinition,
  "OutboundsFct": outboundsFctDefinition,
  "MinWindowFct": minWindowFctDefinition,
  "SlidingAmpGradientNode": slidingAmpGradientDefinition,
  "Difference": differenceDefinition,
  "ESP32": esp32Definition,
  "KickDecay": kickDecayDefinition,
  "SnareDecay": snareDecayDefinition,
  "SinglePeakTrigger": singlePeakTriggerDefinition,
  "EdgeToCenterTrigger": edgeToCenterTriggerDefinition,
  "CenterToEdge": centerToEdgeDefinition,
  "Buffer": bufferDefinition,
  "GroupNode": groupDefinition,
  "Routing": routingDefinition,
  "Gathering": gatheringDefinition,
  "ConstantArray": constantArrayDefinition,
  "Function": functionDefinition,
  "SingleColor": singleColorDefinition,
  "SinArray": sinArrayDefinition,
  "Amplitudes": amplitudesDefinition,
  "Smoothing": smoothingDefinition,
  "LowFilter": lowFilterDefinition,
  "HighFilter": highFilterDefinition,
  "BandFilter": bandFilterDefinition,
  "RMS": rmsDefinition,
  "MidSideEnergy": midSideEnergyDefinition,
  "ZeroCrossingRate": zeroCrossingRateDefinition,
  "CrestFactor": crestFactorDefinition,
  "Entropy": entropyDefinition,
  "SpectralFlux": spectralFluxDefinition,
  "OnsetStrength": onsetStrengthDefinition,
  "SpectralCentroid": spectralCentroidDefinition,
  "PitchClassChroma": pitchClassChromaDefinition,
  "ChromaPrism": chromaPrismDefinition,
  "Window": windowDefinition,
  "AveragedWindowFct": averagedWindowFctDefinition,
  "CeilWindowFct": ceilWindowFctDefinition,
  "DecreasingAvgWindowFct": decreasingAvgWindowFctDefinition,
  "MaxWindowFct": maxWindowFctDefinition,
  "SumWindowFct": sumWindowFctDefinition,
  "BarGraphChart": barGraphChartDefinition,
  "MultiLineChart": multiLineChartDefinition,
  "SingleLineChart": singleLineChartDefinition,
  "Rainbow": rainbowDefinition,
  "Gradiant": gradiantDefinition,
  "BroadcastAddition": broadcastAdditionDefinition,
  "RollingNode": rollingDefinition,
  "ValueTransformer": valueTransformerDefinition,
  "OperatorPipeline": operatorPipelineDefinition,
  "Clip": clipDefinition,
  "PeakFilter": peakFilterDefinition,
  "ThresholdFilter": thresholdFilterDefinition,
  "AvgFrequencies": avgFrequenciesDefinition,
  "LinearAmplitudesTransformer": linearAmplitudesTransformerDefinition,
  "FreqScaledAmplitudesTransformer": freqScaledAmplitudesTransformerDefinition,
  "FctAmplitudesTransformer": fctAmplitudesTransformerDefinition,
  "AmplitudeLevelFunction": amplitudeLevelFunctionDefinition,
  "StreamPlayer": streamPlayerDefinition,
  "StreamMic": streamMicDefinition,
  "SCPlaylistPlayer": soundcloudPlayerDefinition,
  "StemsRecognition": stemsRecognitionDefinition,
  "RGBAPipeline": rgbapipelineDefinition,
  "BroadcastFractionNode": broadcastFractionDefinition,
  "BroadcastIndexesNode": broadcastIndexesDefinition,
  "BroadcastRescalerNode": broadcastRescalerDefinition,
};

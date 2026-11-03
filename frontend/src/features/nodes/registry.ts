import triggerDefinition from "./definitions/trigger/trigger-node.ts";
import outboundsFctDefinition from "./definitions/function/outbounds-fct-node.ts";
import minWindowFctDefinition from "./definitions/windows/min-window-fct-node.ts";
import slidingAmpGradientDefinition from "./definitions/visual/sliding-amp-gradient-node.ts";
import differenceDefinition from "./definitions/transforms/difference-node.ts";
import esp32Definition from "./definitions/controllers/esp32-node.ts";
import kickDecayDefinition from "./definitions/groups/kick-decay-node.ts";
import snareDecayDefinition from "./definitions/groups/snare-decay-node.ts";
import singlePeakTriggerDefinition from "./definitions/groups/single-peak-trigger-node.ts";
import edgeToCenterTriggerDefinition from "./definitions/groups/edge-to-center-trigger-node.ts";
import centerToEdgeDefinition from "./definitions/groups/center-to-edge-node.ts";
import bufferDefinition from "./definitions/buffer/buffer-node.ts";
import groupDefinition from "./definitions/groups/group-node.ts";
import routingDefinition from "./definitions/routing/routing-node.ts";
import gatheringDefinition from "./definitions/routing/gathering-node.ts";
import constantArrayDefinition from "./definitions/simple/constant-array-node.ts";
import functionDefinition from "./definitions/function/function-node.ts";
import singleColorDefinition from "./definitions/visual/single-color-node.ts";
import sinArrayDefinition from "./definitions/simple/sin-array-node.ts";
import amplitudesDefinition from "./definitions/amplitudes/amplitudes-node.ts";
import smoothingDefinition from "./definitions/transforms/smoothing-node.ts";
import lowFilterDefinition from "./definitions/auditory/low-filter-node.ts";
import highFilterDefinition from "./definitions/auditory/high-filter-node.ts";
import bandFilterDefinition from "./definitions/auditory/band-filter-node.ts";
import rmsDefinition from "./definitions/auditory/rms-node.ts";
import midSideEnergyDefinition from "./definitions/features/mid-side-energy-node.ts";
import zeroCrossingRateDefinition from "./definitions/features/zero-crossing-rate-node.ts";
import sinPeriodicityDefinition from "./definitions/features/sin-periodicity-node.ts";
import crestFactorDefinition from "./definitions/features/crest-factor-node.ts";
import entropyDefinition from "./definitions/features/entropy-node.ts";
import spectralFluxDefinition from "./definitions/features/spectral-flux-node.ts";
import onsetStrengthDefinition from "./definitions/features/onset-strength-node.ts";
import spectralCentroidDefinition from "./definitions/features/spectral-centroid-node.ts";
import pitchClassChromaDefinition from "./definitions/features/pitch-class-chroma-node.ts";
import chromaPrismDefinition from "./definitions/features/chroma-prism-node.ts";
import windowDefinition from "./definitions/window/window-node.ts";
import averagedWindowFctDefinition from "./definitions/windows/averaged-window-fct-node.ts";
import ceilWindowFctDefinition from "./definitions/windows/ceil-window-fct-node.ts";
import decreasingAvgWindowFctDefinition from "./definitions/windows/decreasing-avg-window-fct-node.ts";
import maxWindowFctDefinition from "./definitions/windows/max-window-fct-node.ts";
import sumWindowFctDefinition from "./definitions/windows/sum-window-fct-node.ts";
import barGraphChartDefinition from "./definitions/visual/bar-graph-chart-node.ts";
import multiLineChartDefinition from "./definitions/visual/multi-line-chart-node.ts";
import singleLineChartDefinition from "./definitions/visual/single-line-chart-node.ts";
import rainbowDefinition from "./definitions/rainbow/rainbow-node.ts";
import gradiantDefinition from "./definitions/rainbow/gradiant-node.ts";
import broadcastAdditionDefinition from "./definitions/broadcast/broadcast-addition-node.ts";
import rollingDefinition from "./definitions/visual/rolling-node.ts";
import valueTransformerDefinition from "./definitions/transforms/value-transformer-node.ts";
import operatorPipelineDefinition from "./definitions/transforms/operator-pipeline-node.ts";
import clipDefinition from "./definitions/transforms/clip-node.ts";
import peakFilterDefinition from "./definitions/transforms/peak-filter-node.ts";
import thresholdFilterDefinition from "./definitions/transforms/threshold-filter-node.ts";
import avgFrequenciesDefinition from "./definitions/amplitudes/avg-frequencies-node.ts";
import linearAmplitudesTransformerDefinition from "./definitions/amplitudes/linear-amplitudes-transformer-node.ts";
import freqScaledAmplitudesTransformerDefinition from "./definitions/amplitudes/freq-scaled-amplitudes-transformer-node.ts";
import fctAmplitudesTransformerDefinition from "./definitions/amplitudes/fct-amplitudes-transformer-node.ts";
import amplitudeLevelFunctionDefinition from "./definitions/amplitudes/amplitude-level-function-node.ts";
import streamPlayerDefinition from "./definitions/stream/stream-player-node.ts";
import streamMicDefinition from "./definitions/stream/stream-mic-node.ts";
import soundcloudPlayerDefinition from "./definitions/player/soundcloud-player-node.ts";
import stemsRecognitionDefinition from "./definitions/offline/stems-recognition-node.ts";
import rgbapipelineDefinition from "./definitions/visual/rgbapipeline-node.ts";
import broadcastFractionDefinition from "./definitions/broadcast/broadcast-fraction-node.ts";
import broadcastIndexesDefinition from "./definitions/broadcast/broadcast-indexes-node.ts";
import broadcastRescalerDefinition from "./definitions/broadcast/broadcast-rescaler-node.ts";
import type { NodeDefinition } from "./definition.ts";

export const nodeDefinitions: Record<string, NodeDefinition> = {
  Trigger: triggerDefinition,
  OutboundsFct: outboundsFctDefinition,
  MinWindowFct: minWindowFctDefinition,
  SlidingAmpGradientNode: slidingAmpGradientDefinition,
  Difference: differenceDefinition,
  ESP32: esp32Definition,
  KickDecay: kickDecayDefinition,
  SnareDecay: snareDecayDefinition,
  SinglePeakTrigger: singlePeakTriggerDefinition,
  EdgeToCenterTrigger: edgeToCenterTriggerDefinition,
  CenterToEdge: centerToEdgeDefinition,
  Buffer: bufferDefinition,
  GroupNode: groupDefinition,
  Routing: routingDefinition,
  Gathering: gatheringDefinition,
  ConstantArray: constantArrayDefinition,
  Function: functionDefinition,
  SingleColor: singleColorDefinition,
  SinArray: sinArrayDefinition,
  Amplitudes: amplitudesDefinition,
  Smoothing: smoothingDefinition,
  LowFilter: lowFilterDefinition,
  HighFilter: highFilterDefinition,
  BandFilter: bandFilterDefinition,
  RMS: rmsDefinition,
  MidSideEnergy: midSideEnergyDefinition,
  ZeroCrossingRate: zeroCrossingRateDefinition,
  SinPeriodicity: sinPeriodicityDefinition,
  CrestFactor: crestFactorDefinition,
  Entropy: entropyDefinition,
  SpectralFlux: spectralFluxDefinition,
  OnsetStrength: onsetStrengthDefinition,
  SpectralCentroid: spectralCentroidDefinition,
  PitchClassChroma: pitchClassChromaDefinition,
  ChromaPrism: chromaPrismDefinition,
  Window: windowDefinition,
  AveragedWindowFct: averagedWindowFctDefinition,
  CeilWindowFct: ceilWindowFctDefinition,
  DecreasingAvgWindowFct: decreasingAvgWindowFctDefinition,
  MaxWindowFct: maxWindowFctDefinition,
  SumWindowFct: sumWindowFctDefinition,
  BarGraphChart: barGraphChartDefinition,
  MultiLineChart: multiLineChartDefinition,
  SingleLineChart: singleLineChartDefinition,
  Rainbow: rainbowDefinition,
  Gradiant: gradiantDefinition,
  BroadcastAddition: broadcastAdditionDefinition,
  RollingNode: rollingDefinition,
  ValueTransformer: valueTransformerDefinition,
  OperatorPipeline: operatorPipelineDefinition,
  Clip: clipDefinition,
  PeakFilter: peakFilterDefinition,
  ThresholdFilter: thresholdFilterDefinition,
  AvgFrequencies: avgFrequenciesDefinition,
  LinearAmplitudesTransformer: linearAmplitudesTransformerDefinition,
  FreqScaledAmplitudesTransformer: freqScaledAmplitudesTransformerDefinition,
  FctAmplitudesTransformer: fctAmplitudesTransformerDefinition,
  AmplitudeLevelFunction: amplitudeLevelFunctionDefinition,
  StreamPlayer: streamPlayerDefinition,
  StreamMic: streamMicDefinition,
  SCPlaylistPlayer: soundcloudPlayerDefinition,
  StemsRecognition: stemsRecognitionDefinition,
  RGBAPipeline: rgbapipelineDefinition,
  BroadcastFractionNode: broadcastFractionDefinition,
  BroadcastIndexesNode: broadcastIndexesDefinition,
  BroadcastRescalerNode: broadcastRescalerDefinition,
};

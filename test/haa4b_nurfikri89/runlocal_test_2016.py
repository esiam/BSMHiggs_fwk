import FWCore.ParameterSet.Config as cms

from UserCode.bsmhiggs_fwk.mainNtuplizer_cfi import *


from JMEAnalysis.JetToolbox.jetToolbox_cff import jetToolbox

from PhysicsTools.PatAlgos.tools.jetTools import updateJetCollection
from PhysicsTools.PatUtils.tools.runMETCorrectionsAndUncertainties import runMetCorAndUncFromMiniAOD

process.load("FWCore.MessageService.MessageLogger_cfi")
process.MessageLogger.cerr.FwkReport.reportEvery = 1

process.load("PhysicsTools.PatAlgos.producersLayer1.patCandidates_cff")
process.load("Configuration.EventContent.EventContent_cff")
process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(50) )

#load run conditions
process.load('Configuration.Geometry.GeometryIdeal_cff')
process.load('Configuration.StandardSequences.MagneticField_38T_cff')

#------ Declare the correct global tag ------#
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_condDBv2_cff')
process.GlobalTag.globaltag = '106X_mcRun2_asymptotic_v17'

process.options   = cms.untracked.PSet(
   allowUnscheduled = cms.untracked.bool(True)
)

updateJetCollection(
   process,
   jetSource = cms.InputTag('slimmedJets'),
   labelName = 'UpdatedJEC',
   jetCorrections = ('AK4PFchs', cms.vstring(['L1FastJet', 'L2Relative', 'L3Absolute', 'L2L3Residual']), 'None')
# Update: Safe to always add 'L2L3Residual' as MC contains dummy L2L3Residual corrections (always set to 1)
)
from RecoEgamma.EgammaTools.EgammaPostRecoTools import setupEgammaPostRecoSeq
from RecoJets.JetProducers.PileupJetID_cfi import pileupJetId
glob_tag = '106X_mcRun2_asymptotic_v17'
if 'preVFP' in glob_tag:  #check if you are preVFP
   #re-run the Pileup Jet ID
   #https://twiki.cern.ch/twiki/bin/view/CMS/PileupJetIDUL#Recommendations_for_2016_UL_data
   from RecoJets.JetProducers.PileupJetID_cfi import _chsalgos_106X_UL16APV   #(_chsalgos_106X_UL16APV for APV samples)
   process.pileupJetIdUpdated = pileupJetId.clone(
           jets=cms.InputTag('updatedPatJetsUpdatedJEC'),             #(Your JEC corrected jets here),
           inputIsCorrected=True,
           applyJec=False,
           vertexes=cms.InputTag("offlineSlimmedPrimaryVertices"),
           algos = cms.VPSet(_chsalgos_106X_UL16APV),
       )

   #Recipe for running scales and smearings using EgammaPostRecoTools
   #https://twiki.cern.ch/twiki/bin/view/CMS/EgammaUL2016To2018#Scale_and_smearing_corrections_f
   setupEgammaPostRecoSeq(process,
                          runEnergyCorrections=True,
                          runVID=False, #saves CPU time by not needlessly re-running VID, if you want the Fall17V2 IDs, set this to True or remove (default is True)
                          era='2016preVFP-UL')
   #a sequence egammaPostRecoSeq has now been created and should be added to your path, eg process.p=cms.Path(process.egammaPostRecoSeq)
else:
   from RecoJets.JetProducers.PileupJetID_cfi import _chsalgos_106X_UL16
   process.pileupJetIdUpdated = pileupJetId.clone(
      jets=cms.InputTag('updatedPatJetsUpdatedJEC'),
           inputIsCorrected=True,
           applyJec=False,
           vertexes=cms.InputTag("offlineSlimmedPrimaryVertices"),
           algos = cms.VPSet(_chsalgos_106X_UL16),
       )
   setupEgammaPostRecoSeq(process,
                          runEnergyCorrections=True,
                          runVID=False, #saves CPU time
                          era='2016postVFP-UL')

runOnMC=True
if runOnMC:
   runMetCorAndUncFromMiniAOD(process,
            isData=False
         )
else:
   runMetCorAndUncFromMiniAOD(process,
                        isData=True,
                        )

process.mainNtuplizer.isMC = cms.bool(True)
process.mainNtuplizer.dtag = cms.string("MC13TeV_Zh_amass20_2016")
process.mainNtuplizer.xsec = cms.double(1.0)
process.mainNtuplizer.mctruthmode = cms.int32(1)
process.mainNtuplizer.verbose = cms.bool(True)
process.mainNtuplizer.metFilterBitsTag = cms.InputTag('TriggerResults','','HLT')
process.mainNtuplizer.Legacy2016 = cms.bool(True)
process.mainNtuplizer.jetsTag = cms.InputTag('updatedPatJetsUpdatedJEC')
process.mainNtuplizer.fatjetsTag = cms.InputTag('packedPatJetsAK8PFPuppiSoftDrop')



###########################################################
# Workflow 1 START
# Use JetToolbox. Does not seem to work at all.
#
#
############################################################
"""
listBtagDiscriminators = [
     'pfCombinedInclusiveSecondaryVertexV2BJetTags',
     'pfBoostedDoubleSecondaryVertexAK8BJetTags'
]
listBtagSubjetsDiscriminators = [
    'pfDeepCSVJetTags:probb',
    'pfDeepCSVJetTags:probbb'
]

listBtagDiscriminators = None
listBtagSubjetsDiscriminators = None


jetToolbox(process,
   'ak8',
   'JTBSequence',
   'noOutput',
   postFix="JTB",
   runOnMC=True,
   PUMethod='CHS',
   dataTier='miniAOD',
   addSoftDrop = True,
   addSoftDropSubjets = True,
   addNsub = True,
   GetJetMCFlavour = True,
   GetSubjetMCFlavour = True,
   bTagDiscriminators = listBtagDiscriminators,
   subjetBTagDiscriminators = listBtagSubjetsDiscriminators,
   # addEnergyCorrFuncSubjets = True,
   Cut = 'pt > 40.'
)
#
# This is the pt threshold just after jet clustering.
# Set to 5 GeV which is the same as the ungroom collection (by default in CMSSW)
#
process.ak8PFJetsCHSJTBSoftDrop.jetPtMin = 5.


from PhysicsTools.PatAlgos.tools.helpers  import getPatAlgosToolsTask
process.patAlgosToolsTask = getPatAlgosToolsTask(process)

process.finalPatJetsAK8PFCHSJTB = cms.EDFilter("PATJetRefSelector",
   src = cms.InputTag("patJetsAK8PFCHSJTBPATJetswithUserData"),
   cut = cms.string("pt > 40.")
)
# process.patAlgosToolsTask.add(process.finalPatJetsAK8PFCHSJTB)
# process.JTBSequence.insert(process.JTBSequence.index(process.patJetsAK8PFCHSJTBPATJetswithUserData)+1, process.finalPatJetsAK8PFCHSJTB)

# process.mainNtuplizer.fatjetsTag = "patJetsAK8PFCHSJTBPATJetswithUserData"
process.mainNtuplizer.fatjetsTag = "finalPatJetsAK8PFCHSJTB"
"""

###########################################################
# Workflow 2 START
# We try to reproduce slimmedJetsAK8 collection
# like in MiniAOD production but lower the pt cut to as low
# as possible
#
############################################################
from UserCode.bsmhiggs_fwk.puppiJetMETReclusteringTools import puppiAK8ReclusterFromMiniAOD

from RecoBTag.ONNXRuntime.pfDeepBoostedJet_cff import _pfDeepBoostedJetTagsAll as pfDeepBoostedJetTagsAll
from RecoBTag.ONNXRuntime.pfHiggsInteractionNet_cff import _pfHiggsInteractionNetTagsProbs as pfHiggsInteractionNetTagsProbs
from RecoBTag.ONNXRuntime.pfParticleNet_cff import _pfParticleNetJetTagsAll as pfParticleNetJetTagsAll
from RecoBTag.ONNXRuntime.pfParticleNet_cff import _pfParticleNetMassRegressionOutputs

btagDiscriminatorsAK8 = cms.PSet(names = cms.vstring(
# 'pfCombinedSecondaryVertexV2BJetTags',
# 'pfCombinedInclusiveSecondaryVertexV2BJetTags',
# 'pfCombinedMVAV2BJetTags',
'pfDeepCSVJetTags:probb',
'pfDeepCSVJetTags:probc',
'pfDeepCSVJetTags:probudsg',
'pfDeepCSVJetTags:probbb',
'pfBoostedDoubleSecondaryVertexAK8BJetTags',
'pfMassIndependentDeepDoubleBvLV2JetTags:probQCD',
'pfMassIndependentDeepDoubleBvLV2JetTags:probHbb',
'pfMassIndependentDeepDoubleCvLV2JetTags:probQCD',
'pfMassIndependentDeepDoubleCvLV2JetTags:probHcc',
'pfMassIndependentDeepDoubleCvBV2JetTags:probHbb',
'pfMassIndependentDeepDoubleCvBV2JetTags:probHcc',
)
# + pfDeepBoostedJetTagsAll
# + pfParticleNetJetTagsAll
# + pfHiggsInteractionNetTagsProbs
# + _pfParticleNetMassRegressionOutputs
)

btagDiscriminatorsAK8Subjets = cms.PSet(names = cms.vstring(
   'pfDeepCSVJetTags:probb',
   'pfDeepCSVJetTags:probbb',
 )
)

process = puppiAK8ReclusterFromMiniAOD(process,
   runOnMC=True,
   useExistingWeights=True,
   btagDiscriminatorsAK8=btagDiscriminatorsAK8,
   btagDiscriminatorsAK8Subjets=btagDiscriminatorsAK8Subjets,
   reclusterAK8GenJets=True
)

#
# Fikri: For whatever reason, we need to explicitly do this.
# Why don't "addJetCollection()" do this for us?
process.patAlgosToolsTask.add(process.patJetPartons)

###############################
# Override some configurations
# for reclustered AK8 Gen jets
###############################
process.ak8GenJetsNoNu.jetPtMin = 10
process.ak8GenJetsNoNuSoftDrop.jetPtMin = 10
process.ak8GenJetsNoNuConstituents.cut = "pt > 10"

#################################
# Override some configurations
# for reclustered AK8 Puppi jets
#################################
process.ak8PFJetsPuppi.jetPtMin = 15
process.ak8PFJetsPuppiSoftDrop.jetPtMin = 15
process.ak8PFJetsPuppiConstituents.cut = "pt > 15. && abs(rapidity()) < 2.4"

finalAK8PuppiPt = 30
process.selectedPatJetsAK8Puppi.cut = "pt > {}".format(finalAK8PuppiPt)
process.selectedPatJetsAK8Puppi.cutLoose = ""
process.selectedPatJetsAK8Puppi.nLoose = 0
process.slimmedJetsAK8NoDeepTags.dropDaughters = cms.string("pt < {}".format(finalAK8PuppiPt))
process.slimmedJetsAK8NoDeepTags.dropSpecific = cms.string("pt < {}".format(finalAK8PuppiPt))
process.slimmedJetsAK8NoDeepTags.dropTagInfos = cms.string("pt < {}".format(finalAK8PuppiPt))

#################################
# For reclustered AK8 Puppi jets
#################################
process.mainNtuplizer.fatjetsTag = "slimmedJetsAK8"

#######################################################
#
# Workflow 2 END
#
#######################################################
process.source = cms.Source("PoolSource",
   fileNames = cms.untracked.vstring("/store/mc/RunIISummer20UL16MiniAODv2/SUSY_ZH_ZToAll_HToAATo4B_M-20_TuneCP5_13TeV_madgraph_pythia8/MINIAODSIM/106X_mcRun2_asymptotic_v17-v2/260000/4A68184A-6942-4B4E-99FD-690E0ABD4520.root"),
)

process.TFileService = cms.Service("TFileService",
   fileName = cms.string("analysis_ZHToAATo4B_M20.root")
)

process.pathRunPatAlgos = cms.Path(process.patAlgosToolsTask)
process.p = cms.Path(
   process.patJetCorrFactorsUpdatedJEC *
   process.updatedPatJetsUpdatedJEC *
   process.pileupJetIdUpdated *
   process.fullPatMetSequence *
   process.egammaPostRecoSeq *
   # process.JTBSequence *
   process.mainNtuplizer
)



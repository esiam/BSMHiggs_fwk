#!/usr/bin/env python
import os,sys
import glob
import json
import ROOT
import getopt
import commands

#print usage
def usage() :
    print ' '
    print 'runLocalAnalysisOverSamples.py [options]'
    print '  -s : submit to queue'
    print '  -b : btagging folder'
    print '  -e : executable name'
    print '  -j : json file containing the samples'
    print '  -d : input dir with the event summaries'
    print '  -o : output directory'
    print '  -c : templated configuration file to steer the job'
    print '  -l : luminosity (pb)'
    print '  -p : extra parameters configure'
    print '  -t : tag to match sample'
    print '  -g : log file from submitting to queue' #RJ
    print '  -r : resubmit failed jobs'
    print ' '
    exit(-1)

"""
Gets the value of a given item
(if not available a default value is returned)
"""
def getByLabel(desc,key,defaultVal=None) :
    try :
        return desc[key]
    except KeyError:
        return defaultVal


#parse the options
try:
     # retrive command line options
     shortopts  = "s:b:e:j:d:o:c:l:p:t:g:r:?" #RJ
     opts, args = getopt.getopt( sys.argv[1:], shortopts )
except getopt.GetoptError:
     # print help information and exit:
     print "ERROR: unknown options in argument %s" % sys.argv[1:]
     usage()
     sys.exit(1)

subtoBatch=False
requirementtoBatch='type==SLC6_64&&pool>30000'
samplesDB=''
theExecutable=''
inputdir=''
outdir=''
btagDir=''
lumi=1
cfg_file=''
split=1
segment=0
params=''
onlytag='all'
queuelog=''
resubmit=False

DtagsList = []
count=0
who = commands.getstatusoutput('whoami')[1]
SCRIPT = open('/tmp/'+who+'/SCRIPT_Submit2batch.sh',"w")
SCRIPT_L = open('/tmp/'+who+'/SCRIPT_Local.sh',"w")
SCRIPT_L.writelines('#!bin/sh \n\n')
SCRIPT_L.writelines('cd $CMSSW_BASE/src/UserCode/bsmhiggs_fwk/; \n\n')

for o,a in opts:
    if o in("-?", "-h"):
        usage()
        sys.exit(0)
    elif o in('-s'):
        subtoBatch=True
        queue=a
        if(queue=="True") : queue="tomorrow"
    elif o in('-j'): samplesDB = a
    elif o in('-e'): theExecutable = a
    elif o in('-d'): inputdir = a
    elif o in('-o'): outdir = a
    elif o in('-b'): btagDir = a
    elif o in('-l'): lumi=float(a)
    elif o in('-c'): cfg_file = a
    elif o in('-p'): params = a
    elif o in('-t'): onlytag = a
    elif o in('-g'): queuelog = a #RJ
    elif o in('-r'): resubmit = a

#open the file which describes the sample
jsonFile = open(samplesDB,'r')
procList=json.load(jsonFile,encoding='utf-8').items()

print "Only files with dtags matching " + onlytag + " are processed."
#run over sample
for proc in procList :

    #run over processes
    for desc in proc[1] :

        #run over items in process
        isdata=getByLabel(desc,'isdata',False)
        mctruthmode=getByLabel(desc,'mctruthmode',0)
        tag = getByLabel(desc,'tag','') #RJ
        print tag

        mytag = tag
        mytag = mytag.replace("#","")
        mytag = mytag.replace(" ","")
        mytag = mytag.replace("(","")
        mytag = mytag.replace(")","")
        mytag = mytag.replace("{","")
        mytag = mytag.replace("}","")
        mytag = mytag.replace("+","")
    ## split jobs by tag name
        SCRIPT_Temp = open('/tmp/'+who+'/SCRIPT_Local_'+mytag+'.sh',"w")
        SCRIPT_Temp.writelines('#!bin/sh \n\n')
        SCRIPT_Temp.writelines('cd $CMSSW_BASE/src/UserCode/bsmhiggs_fwk/; \n\n')

        data = desc['data']
        for d in data :
            origdtag = getByLabel(d,'dtag','')
            dtag = origdtag
            xsec = getByLabel(d,'xsec',-1)
            br = getByLabel(d,'br',[])
            suffix = str(getByLabel(d,'suffix' ,""))
            if(onlytag!='all') :
                if(dtag.find(onlytag)<0) : continue
            if(mctruthmode!=0) : dtag+='_filt'+str(mctruthmode)
            PythonLists = open('/tmp/'+who+'/'+dtag+'_PythonList.txt',"w")
            SCRIPT2HTCondor = open('/tmp/'+who+'/'+dtag+'_SubmitHTCondor.sub',"w")
            SCRIPT2HTCondor.writelines('#This HTCondor job submission script is generated by automatically runLocalAnalysisOverSamples.py\n\n')

            if(xsec>0 and not isdata) :
                for ibr in br :  xsec = xsec*ibr
            split=getByLabel(d,'split',1)
#            print "Running 133"

            ## submit or resubmit
            if(resubmit) :
                status, output = commands.getstatusoutput('ls ' + outdir +'/'+ dtag + '_' + '*_cfg.py')
                if status > 0 :
                    print "No python configuation files for tag: " + dtag 
                    continue
                configList = output.split('\n')
                failedList = []
                print "Collecting python configuration files for tag: " + dtag 

                    ## split jobs by dtag name
                SCRIPT_DTag = open('/tmp/'+who+'/SCRIPT_Local_'+dtag+'.sh',"w")
                SCRIPT_DTag.writelines('#!bin/sh \n\n')
                SCRIPT_DTag.writelines('cd $CMSSW_BASE/src/UserCode/bsmhiggs_fwk/; \n\n')
                
                for cfgfile in configList:
                    if( not os.path.isfile( cfgfile.replace('_cfg.py','.root'))):
                        failedList+= [cfgfile]
                if(len(failedList)>0):
                    rsegment=0
                    for cfgfile in failedList: 
                        os.system('mkdir -p ' + queuelog)
                        htlog = os.path.join( queuelog, 'HTCondor_Data')
                        if(not isdata):
                            htlog = os.path.join( queuelog, 'HTCondor_MC')
                        os.system('mkdir -p ' + htlog)
                        SCRIPT.writelines('submit2batch.sh -q'+queue+' -G'+queuelog+'/'+dtag+'_'+str(rsegment)+'.log'+' -R"' + requirementtoBatch + '" -J' + dtag + str(rsegment) + ' ${CMSSW_BASE}/bin/${SCRAM_ARCH}/wrapLocalAnalysisRun.sh ' + theExecutable + ' ' + cfgfile + '\n\n')
                        SCRIPT_L.writelines(theExecutable + ' ' + cfgfile + ' >& '+queuelog+'/'+dtag+str(rsegment)+'.log'+' & \n\n')
                        count = count + 1
                        
                        SCRIPT_Temp.writelines(theExecutable + ' ' + cfgfile + ' >& '+queuelog+'/'+dtag+'_'+str(rsegment)+'.log'+' & \n\n')
                        SCRIPT_DTag.writelines(theExecutable + ' ' + cfgfile + ' >& '+queuelog+'/'+dtag+'_'+str(rsegment)+'.log'+' & \n\n')
                        PythonLists.writelines(cfgfile+' '+htlog+'/'+dtag+'_'+str(rsegment)+'\n')
                        #sys.exit(0)
#                        os.system('submit2batch.sh -q'+queue+' -G'+queuelog+'/'+dtag+'_'+str(rsegment)+'.log'+' -R"' + requirementtoBatch + '" -J' + dtag + str(rsegment) + ' ${CMSSW_BASE}/bin/${SCRAM_ARCH}/wrapLocalAnalysisRun.sh ' + theExecutable + ' ' + cfgfile)
                        rsegment+=1 

            else :    
#                print "Running 165"
                print "Generating python configuration files for tag: " + dtag
                mydtag = dtag
                mydtag = mydtag.replace("#","")
                mydtag = mydtag.replace(" ","")
                mydtag = mydtag.replace("(","")
                mydtag = mydtag.replace(")","")
                mydtag = mydtag.replace("{","")
                mydtag = mydtag.replace("}","")
                mydtag = mydtag.replace("+","")
            ## split jobs by dtag name
                SCRIPT_DTag = open('/tmp/'+who+'/SCRIPT_Local_'+mydtag+'.sh',"w")
                SCRIPT_DTag.writelines('#!bin/sh \n\n')
                SCRIPT_DTag.writelines('cd $CMSSW_BASE/src/UserCode/bsmhiggs_fwk/; \n\n')
                
            # Loop over files for given dtag name:
                ntplpath = '/eos/cms/store/user/' + who + '/'+inputdir + '/*/crab_' + origdtag + '*/*/*/'
                # FileList = [file for file in glob.glob(ntplpath+'analysis_*.root')] 
                
                segment=0
                for file in glob.glob(ntplpath+'analysis_*.root'):
                    eventsFile = file
#            eventsFile = ', \n '.join('"' + item + '"' for item in FileList)
                    
                    sedcmd = 'sed \"s%"@input"%' +eventsFile +'%;'
                    sedcmd += 's%"@outdir"%' + outdir +'%;s%@isMC%' + str(not isdata) + '%;s%@mctruthmode%'+str(mctruthmode)+'%;s%@xsec%'+str(xsec)+'%;'
                    sedcmd += 's%"@btagDir"%' + btagDir + '%;'
                    sedcmd += 's%"@suffix"%' + suffix + '%;'
                    sedcmd += 's%"@proc"%' + dtag + '%;'
                    sedcmd += 's%"@tag"%' +(dtag + suffix + '_' + str(segment))+'%;'#RJ
                #                sedcmd += 's%"@tag"%' +str(getByLabel(desc,'tag',-1))+'%;'#RJ
                    if(params.find('@useMVA')<0) :          params = '@useMVA=False ' + params
                    if(params.find('@evStart')<0) :         params = '@evStart=0 ' + params
                    if(params.find('@evEnd')<0) :           params = '@evEnd=-1 ' + params
                    if(params.find('@saveSummaryTree')<0) : params = '@saveSummaryTree=False ' + params
                    if(params.find('@runSystematics')<0) :  params = '@runSystematics=False ' + params
                    if(params.find('@usemetNoHF')<0) :  	params = '@usemetNoHF=False ' + params
                    if(params.find('@useDeepCSV')<0) :      params = '@useDeepCSV=False ' + params
                    if(params.find('@runQCD')<0) :          params = '@runQCD=False ' + params
                    if(params.find('@runMVA')<0) :          params = '@runMVA=False ' + params
                    if(len(params)>0) :
                        extracfgs = params.split(' ')
                        for icfg in extracfgs :
                            varopt=icfg.split('=')
                            if(len(varopt)<2) : continue
                            sedcmd += 's%' + varopt[0] + '%' + varopt[1] + '%;'
                    sedcmd += '\"'
                        
                    
                    cfgfile=outdir +'/'+ dtag + suffix + '_' + str(segment) + '_cfg.py'
#                    print cfgfile    
                    os.system('cat ' + cfg_file + ' | ' + sedcmd + ' > ' + cfgfile)

                    if(not subtoBatch) :
                        os.system(theExecutable + ' ' + cfgfile)
                    else :
                        os.system('mkdir -p ' + queuelog)
                        htlog = os.path.join( queuelog, 'HTCondor_Data')
                        if(not isdata): 
                            htlog = os.path.join( queuelog, 'HTCondor_MC')
                        os.system('mkdir -p ' + htlog)
                        
                        SCRIPT.writelines('submit2batch.sh -q'+queue+' -G'+queuelog+'/'+dtag+'_'+str(segment)+'.log'+' -R"' + requirementtoBatch + '" -J' + dtag + str(segment) + ' ${CMSSW_BASE}/bin/${SCRAM_ARCH}/wrapLocalAnalysisRun.sh ' + theExecutable + ' ' + cfgfile + '\n\n')
                        SCRIPT_L.writelines(theExecutable + ' ' + cfgfile + ' >& '+queuelog+'/'+dtag+str(segment)+'.log'+' & \n\n')
                        count = count + 1
                        
                        SCRIPT_Temp.writelines(theExecutable + ' ' + cfgfile + ' >& '+queuelog+'/'+dtag+'_'+str(segment)+'.log'+' & \n\n')
                        SCRIPT_DTag.writelines(theExecutable + ' ' + cfgfile + ' >& '+queuelog+'/'+dtag+'_'+str(segment)+'.log'+' & \n\n')
                        PythonLists.writelines(cfgfile+' '+htlog+'/'+dtag+'_'+str(segment)+'\n')
                        #sys.exit(0)
#                        os.system('submit2batch.sh -q'+queue+' -G'+queuelog+'/'+dtag+'_'+str(segment)+'.log'+' -R"' + requirementtoBatch + '" -J' + dtag + str(segment) + ' ${CMSSW_BASE}/bin/${SCRAM_ARCH}/wrapLocalAnalysisRun.sh ' + theExecutable + ' ' + cfgfile)

                    segment += 1 #increment counter for job split

                SCRIPT_DTag.writelines('cd -;')
                SCRIPT_DTag.close()
                os.system('chmod u+x,g-r,o-r '+'/tmp/'+who+'/SCRIPT_Local_'+mydtag+'.sh ')
                os.system('mkdir -p '+queuelog+'/split/')
                os.system('mkdir -p '+queuelog+'/all/')
                os.system('mv /tmp/'+who+'/SCRIPT_Local_'+mydtag+'.sh '+queuelog+'/split')

            PythonLists.close()
            if(os.stat("/tmp/"+who+'/'+dtag+'_PythonList.txt').st_size > 0):
                SCRIPT2HTCondor.writelines('executable            = '+os.environ.get('CMSSW_BASE')+'/bin/'+os.environ.get('SCRAM_ARCH')+'/wrapLocalAnalysisRun.sh\n')
                SCRIPT2HTCondor.writelines('arguments             = '+'"'+os.environ.get('CMSSW_BASE')+'/bin/'+os.environ.get('SCRAM_ARCH')+'/'+theExecutable+' $(cfg)"'+'\n')
                SCRIPT2HTCondor.writelines('transfer_input_files  = '+os.environ.get('CMSSW_BASE')+'/bin/'+os.environ.get('SCRAM_ARCH')+'/'+theExecutable+', $(cfg)'+'\n')
                SCRIPT2HTCondor.writelines('output                = $(log).out\n')
                SCRIPT2HTCondor.writelines('error                 = $(log).err\n')
                SCRIPT2HTCondor.writelines('log                   = $(log).log\n')
                SCRIPT2HTCondor.writelines('request_cpus          = 6\n')
                SCRIPT2HTCondor.writelines('+JobFlavour           = "'+queue+'"\n')
                SCRIPT2HTCondor.writelines('queue cfg,log from '+queuelog+'/all/'+dtag+'_PythonList.txt')
                SCRIPT2HTCondor.close()
                os.system('mv /tmp/'+who+'/'+dtag+'_PythonList.txt '+queuelog+'/all/')
                os.system('mv /tmp/'+who+'/'+dtag+'_SubmitHTCondor.sub '+queuelog+'/all/')
                DtagsList.append(dtag)
#                print('\033[92mSubmitting jobs for: '+dtag+' \033[0m')
#                os.system('condor_submit '+queuelog+'/all/'+dtag+'_SubmitHTCondor.sub')
            else:
                SCRIPT2HTCondor.close()
                os.system('rm /tmp/'+who+'/'+dtag+'_PythonList.txt')
                os.system('rm /tmp/'+who+'/'+dtag+'_SubmitHTCondor.sub')
            
        SCRIPT_Temp.writelines('cd -;')
        SCRIPT_Temp.close()
        os.system('chmod u+x,g-r,o-r '+'/tmp/'+who+'/SCRIPT_Local_'+mytag+'.sh ')
        os.system('mkdir -p '+queuelog+'/combine/')
        os.system('mv /tmp/'+who+'/SCRIPT_Local_'+mytag+'.sh '+queuelog+'/combine/')
                
SCRIPT.close()
SCRIPT_L.writelines('cd -;')
SCRIPT_L.close()
os.system('chmod u+x,g-r,o-r '+'/tmp/'+who+'/SCRIPT_Submit2batch.sh '+'/tmp/'+who+'/SCRIPT_Local.sh ')
os.system('mv /tmp/'+who+'/SCRIPT_Submit2batch.sh '+queuelog+'/all/')
os.system('mv /tmp/'+who+'/SCRIPT_Local.sh '+queuelog+'/all/')
os.system('cp $CMSSW_BASE/src/UserCode/bsmhiggs_fwk/scripts/splitlocaljobs.py '+queuelog+'/all/')
os.system('cp $CMSSW_BASE/src/UserCode/bsmhiggs_fwk/scripts/checkLocaljobs.py '+queuelog+'/all/')
# Now submit jobs
for tag in DtagsList:
#    pythonFile = queuelog+'/all/'+dtag+'_PythonList.txt'
#    f = open(pythonFile)
#    try:
#        for line in f:
#            print line.split()[0]
#    finally:
#        f.close()
    print('\033[92mSubmitting jobs for: '+tag+' \033[0m')
    os.system('condor_submit '+queuelog+'/all/'+tag+'_SubmitHTCondor.sub')
print('\033[92mJobs submitted, use condor_q to check status. \033[0m')

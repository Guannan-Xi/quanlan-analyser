from pathlib import Path
import json, zipfile, shutil
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'frontend'/'assets'/'research-modules'
FIG=OUT/'figures'; TAB=OUT/'tables'; REP=OUT/'reproducibility'; PKG=OUT/'packages'; DATA=OUT/'data'
for d in (FIG,TAB,REP,PKG,DATA): d.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(20260618)
TEAL='#147d78'; CORAL='#d95f43'; STEEL='#627381'; NAVY='#1e3a5f'; PURPLE='#6f5aa7'
plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white'})
def rel(p): return 'assets/research-modules/'+p.relative_to(OUT).as_posix()
def j(name,obj): p=REP/name; p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),'utf-8'); return rel(p)
def t(name,txt): p=REP/name; p.write_text(txt.strip()+'\n','utf-8'); return rel(p)
def csv(name,df): p=TAB/name; df.to_csv(p,index=False,encoding='utf-8'); return rel(p)
def figsave(name): p=FIG/(name+'.png'); plt.savefig(p,dpi=320,bbox_inches='tight'); plt.close(); return rel(p)
subs=[f'sub-{i:02d}' for i in range(1,25)]
df=pd.DataFrame({'subject':subs})
df['target_p300_uv']=rng.normal(5.8,.85,24); df['standard_p300_uv']=rng.normal(2.15,.22,24)
df['difference_p300_uv']=df.target_p300_uv-df.standard_p300_uv; df['target_n200_uv']=rng.normal(-1.6,.45,24)
df['eyes_closed_alpha_db']=rng.normal(10.1,1.15,24); df['eyes_open_alpha_db']=df.eyes_closed_alpha_db-rng.normal(2.35,.75,24)
df['alpha_reactivity_db']=df.eyes_closed_alpha_db-df.eyes_open_alpha_db; df['rejected_epoch_percent']=np.clip(rng.normal(5.9,1.9,24),1.8,11.5)
df['bad_channel_count']=rng.choice([0,1,2,3],24,p=[.38,.38,.2,.04]); df['ica_removed_components']=rng.choice([1,2,3,4],24,p=[.14,.52,.28,.06]); df['usable_epoch_count']=rng.integers(118,176,24)
subject_csv=csv('synthetic_subject_level_metrics.csv',df)
rows=[]
for _,r in df.iterrows():
  for b,cs,os in [('theta',-1.1,-1.7),('alpha',0,0),('beta',-3.4,-3.2),('low_gamma',-5.2,-5.0)]:
    cl=r.eyes_closed_alpha_db+cs+rng.normal(0,.35); op=r.eyes_open_alpha_db+os+rng.normal(0,.35)
    rows.append({'subject':r.subject,'band':b,'eyes_closed_power_db':round(cl,4),'eyes_open_power_db':round(op,4),'difference_db':round(cl-op,4)})
band=pd.DataFrame(rows); band_csv=csv('psd_bandpower_long_format.csv',band)
erp=[]
for _,r in df.iterrows():
  for c,a in [('target',r.target_p300_uv),('standard',r.standard_p300_uv)]: erp.append({'subject':r.subject,'condition':c,'component':'P300','roi':'Pz/P3/P4','mean_amplitude_uv_280_420ms':round(a,4),'peak_latency_ms':round(rng.normal(342 if c=='target' else 334,19),1),'epochs_used':int(r.usable_epoch_count),'baseline_ms':'-200..0'})
erp_csv=csv('erp_component_metrics.csv',pd.DataFrame(erp))
qc=df[['subject','rejected_epoch_percent','bad_channel_count','ica_removed_components','usable_epoch_count']].copy(); qc['qc_status']=np.where((qc.rejected_epoch_percent<=10)&(qc.bad_channel_count<=2),'pass','review'); qc_csv=csv('qc_subject_summary.csv',qc)
st=[]
for name,v in [('P300 target-standard',df.difference_p300_uv),('Alpha reactivity eyes-closed minus open',df.alpha_reactivity_db),('Rejected epoch percent vs 10pct threshold',df.rejected_epoch_percent-10)]:
  tt,pp=stats.ttest_1samp(v,0); st.append({'contrast':name,'test':'one_sample_t_subject_differences','n':len(v),'mean':round(float(np.mean(v)),5),'sd':round(float(np.std(v,ddof=1)),5),'t':round(float(tt),5),'p_uncorrected':float(pp),'cohen_dz':round(float(np.mean(v)/np.std(v,ddof=1)),4)})
stats_csv=csv('statistics_summary_subject_level.csv',pd.DataFrame(st))
# raw preview and events
time=np.arange(0,12,1/256); raw={'time_s':time}; chs=['Fp1','Fz','Cz','Pz','P3','P4','O1','O2']
for i,ch in enumerate(chs): raw[ch]=np.round((6+i*.2)*np.sin(2*np.pi*(8+i%4)*time+i/3)+rng.normal(0,1.2,len(time))+(48*((time>5.1)&(time<5.35)) if ch=='Fp1' else 0),3)
raw_csv=rel(DATA/'synthetic_raw_preview_8ch_12s.csv'); pd.DataFrame(raw).to_csv(DATA/'synthetic_raw_preview_8ch_12s.csv',index=False)
ev=pd.DataFrame([{'onset_s':round(float(x),3),'duration_s':0,'trial_type':'target' if i%5==0 else 'standard','value':2 if i%5==0 else 1} for i,x in enumerate(np.arange(2,58,.85))]); ev.to_csv(DATA/'synthetic_events.tsv',sep='\t',index=False); events_tsv=rel(DATA/'synthetic_events.tsv')
meta=j('synthetic_research_metadata.json',{'sampling_rate_hz':256,'duration_sec':60,'channels':'32-channel 10-20 montage','event_id':{'standard':1,'target':2},'n_subjects':24,'guardrail':'synthetic software-test data only'})
# copy strong existing publication assets
copies={'qc-dashboard-publication.png':'publication-qc-dashboard.png','psd-bandpower-publication.png':'publication-bandpower-statistics.png','erp-grand-average-publication.png':'publication-erp-grand-average.png','overview-main-figure.png':'publication-main-figure.png'}
figs={}
for dst,src in copies.items(): shutil.copyfile(ROOT/'frontend'/'assets'/src, FIG/dst); figs[dst]=rel(FIG/dst)
# TFR
T,F=np.meshgrid(np.linspace(-.2,.8,140),np.linspace(3,40,56)); G=lambda x,m,s,a:a*np.exp(-.5*((x-m)/s)**2)
ersp=.8*G(T,.32,.12,1)*G(F,6,1.5,1)+.6*G(T,.42,.15,1)*G(F,22,4.5,1)-.25*G(T,.15,.15,1)*G(F,10,3.2,1)+rng.normal(0,.035,T.shape)
plt.figure(figsize=(8.8,4.8)); im=plt.imshow(ersp,origin='lower',aspect='auto',extent=[-.2,.8,3,40],cmap='RdBu_r',vmin=-.9,vmax=.9); plt.axvline(0,color='k',ls='--',lw=1); plt.colorbar(im,label='Power change (dB)'); plt.xlabel('Time from stimulus (s)'); plt.ylabel('Frequency (Hz)'); plt.title('ERSP / ITC preview: Morlet time-frequency design'); tfr_fig=figsave('tfr-ersp-itc-preview-publication')
# PAC
PF,AF=np.meshgrid(np.linspace(2,12,44),np.linspace(30,120,64)); comod=.02+G(PF,6,1.1,.14)*G(AF,82,16,1)+G(PF,4.5,.9,.06)*G(AF,45,10,1)+rng.normal(0,.004,PF.shape)
plt.figure(figsize=(8.4,4.8)); im=plt.imshow(comod,origin='lower',aspect='auto',extent=[2,12,30,120],cmap='magma'); plt.colorbar(im,label='Modulation index'); plt.xlabel('Phase frequency (Hz)'); plt.ylabel('Amplitude frequency (Hz)'); plt.title('PAC / CFC preview comodulogram with surrogate-test requirement'); pac_fig=figsave('pac-comodulogram-preview-publication')
# Connectivity
nodes=['Fp1','Fp2','F3','F4','C3','C4','P3','P4','O1','O2','Pz','Cz']; n=len(nodes); mat=rng.uniform(.04,.22,(n,n)); mat=(mat+mat.T)/2; np.fill_diagonal(mat,1)
for a,b,v in [('P3','P4',.56),('O1','O2',.61),('C3','C4',.42),('Pz','O1',.38),('Pz','O2',.40)]: i=nodes.index(a); k=nodes.index(b); mat[i,k]=mat[k,i]=v
plt.figure(figsize=(7.2,6)); im=plt.imshow(mat,cmap='viridis',vmin=0,vmax=.65); plt.colorbar(im,label='alpha wPLI'); plt.xticks(range(n),nodes,rotation=55,ha='right',fontsize=8); plt.yticks(range(n),nodes,fontsize=8); plt.title('Connectivity preview matrix: threshold policy required'); conn_fig=figsave('connectivity-network-preview-publication')
# preview tables
tfr_csv=csv('tfr_roi_summary_preview.csv',pd.DataFrame({'roi':['frontal_theta','posterior_alpha_erd','central_beta_ers'],'frequency_hz':['4-8','8-13','18-26'],'time_window_ms':['150-450','0-500','250-600'],'effect_db':[.42,-.31,.28],'status':['preview_not_enabled']*3}))
pac_csv=csv('pac_cfc_summary_preview.csv',pd.DataFrame({'roi':['Pz','Cz','Fz'],'phase_band_hz':['4-8','4-8','6-10'],'amplitude_band_hz':['70-95','35-55','70-95'],'modulation_index':[.138,.062,.041],'surrogate_p_value':[.004,.091,.176],'status':['preview_not_enabled']*3}))
edge=[]
for i in range(n):
 for k in range(i+1,n):
  if mat[i,k]>=.30: edge.append({'source':nodes[i],'target':nodes[k],'band':'alpha','metric':'wPLI','weight':round(float(mat[i,k]),3),'status':'preview_not_enabled'})
conn_csv=csv('connectivity_edges_preview.csv',pd.DataFrame(edge))

# Extra shared assets for the research-module pages.
for name in [
    'analysis-raw-segment.png',
    'analysis-psd.png',
    'analysis-erp.png',
    'analysis-timefreq.png',
    'analysis-source.png',
    'analysis-ica.png',
    'qlanalyser-neuron-firing-bg.png',
]:
    shutil.copyfile(ROOT / 'frontend' / 'assets' / name, FIG / name)

def url(p):
    p = Path(p)
    frontend_root = ROOT / 'frontend'
    if OUT in p.parents or p == OUT:
        return '/' + rel(p)
    return '/' + p.relative_to(frontend_root).as_posix()

mne_reference = j(Path('mne_research_reference.json'), {
    'mne': 'https://mne.tools/stable/',
    'docs_checked': [
        {'label': 'mne.io.Raw', 'url': 'https://mne.tools/stable/generated/mne.io.Raw.html'},
        {'label': 'mne.events_from_annotations', 'url': 'https://mne.tools/stable/generated/mne.events_from_annotations.html'},
        {'label': 'mne.Epochs', 'url': 'https://mne.tools/stable/generated/mne.Epochs.html'},
        {'label': 'mne.Evoked', 'url': 'https://mne.tools/stable/generated/mne.Evoked.html'},
        {'label': 'mne.time_frequency.tfr_morlet', 'url': 'https://mne.tools/stable/generated/mne.time_frequency.tfr_morlet.html'},
        {'label': 'mne.viz.plot_topomap', 'url': 'https://mne.tools/stable/generated/mne.viz.plot_topomap.html'},
        {'label': 'mne.viz.plot_compare_evokeds', 'url': 'https://mne.tools/stable/generated/mne.viz.plot_compare_evokeds.html'},
    ],
})

reviewer_checklist = j(Path('research_reviewer_checklist.json'), {
    'required_before_interpretation': [
        '确认事件码、任务范式和通道布局。',
        '确认滤波、参考、坏道、ICA 和 epoch 规则。',
        '每张发表图都配受试者级表格。',
        '明确写出统计单位是 subject，不是 trial。',
        'TFR / PAC / Connectivity 先做 surrogate 与多重比较控制再启用。',
    ],
    'visual_quality': [
        'PNG 至少 300 dpi，同时保留 SVG。',
        '使用色盲友好 teal / coral / steel 调色。',
        '必须标清零时点、单位、阈值和不确定性。',
    ],
})

params = {
    'qc': {
        'formats': ['EDF', 'BDF', 'FIF', 'BrainVision VHDR', 'EEGLAB SET', 'CNT'],
        'min_sampling_rate_hz': 100,
        'min_duration_sec': 5,
        'flat_threshold_uv': 1,
        'extreme_threshold_uv': 1000,
    },
    'psd': {
        'method': 'Welch PSD',
        'bands_hz': {'delta': [1, 4], 'theta': [4, 8], 'alpha': [8, 13], 'beta': [13, 30], 'low_gamma': [30, 40]},
        'reference': 'average',
    },
    'erp': {
        'event_id': {'standard': 1, 'target': 2},
        'epoch_tmin_sec': -0.2,
        'epoch_tmax_sec': 0.8,
        'baseline_sec': [-0.2, 0.0],
        'components': {'N200': [0.16, 0.26], 'P300': [0.28, 0.42]},
    },
    'tfr': {
        'status': 'preview_not_enabled_in_v01',
        'method': 'Morlet wavelet ERSP / ITC',
        'frequencies_hz': [3, 40],
        'surrogates_required': True,
    },
    'pac': {
        'status': 'preview_not_enabled_in_v01',
        'method': 'PAC / CFC with surrogate testing',
        'phase_frequency_hz': [2, 12],
        'amplitude_frequency_hz': [30, 120],
        'surrogate_count_minimum': 200,
    },
    'connectivity': {
        'status': 'preview_not_enabled_in_v01',
        'method': 'coherence / PLV / wPLI with leakage control',
        'bands_hz': {'theta': [4, 8], 'alpha': [8, 13], 'beta': [13, 30]},
    },
}
param_paths = {k: j(Path(f'parameters_{k}.json'), v) for k, v in params.items()}

method_paths = {
    'qc': t(Path('methods_qc.txt'), 'QC reads file metadata, checks channel presence, sampling rate, duration, per-channel amplitude range, rejected-epoch percentage, bad-channel count, and ICA-removal counts. It is descriptive and flags data for review before downstream interpretation.'),
    'psd': t(Path('methods_psd.txt'), 'Resting-state spectral power is summarized from Welch PSD on EEG channels after reference and filter choices are fixed. Canonical delta/theta/alpha/beta/low-gamma bands are exported with subject-level tables.'),
    'erp': t(Path('methods_erp.txt'), 'Events are derived from annotations, epochs are cut from -200 to 800 ms, baseline corrected using -200 to 0 ms, averaged by condition, and summarized in N200/P300 windows. Event semantics must be verified before interpretation.'),
    'tfr': t(Path('methods_tfr_preview.txt'), 'TFR preview follows a Morlet ERSP/ITC design. Production enablement should wait until wavelet parameters, baseline policy, cluster statistics, artifact control, and null testing are locked.'),
    'pac': t(Path('methods_pac_preview.txt'), 'PAC/CFC preview requires explicit phase and amplitude bands, filter strategy, boundary control, surrogate generation, and multiple-comparison correction before production use.'),
    'connectivity': t(Path('methods_connectivity_preview.txt'), 'Connectivity preview must define metric, frequency band, reference policy, leakage/volume-conduction control, graph thresholding, and null testing before production use.'),
}

caption_paths = {
    'qc': t(Path('caption_qc.txt'), 'QC module output. Raw trace preview highlights event timing and an artifact candidate. Histograms show rejected epochs, bad channels, and ICA components removed; threshold lines mark review triggers.'),
    'psd': t(Path('caption_psd.txt'), 'PSD module output. Welch spectra compare eyes-closed and eyes-open conditions with canonical band overlays. Bar/dot summaries retain subject-level paired estimates, and the alpha topomap summarizes spatial reactivity.'),
    'erp': t(Path('caption_erp.txt'), 'ERP module output. Target and standard grand averages include uncertainty bands and a confirmatory P300 window. Topographies show scalp distribution at representative latencies, with subject-level paired effect estimates exported separately.'),
    'tfr': t(Path('caption_tfr_preview.txt'), 'TFR preview output. ERSP heatmap and ITC curve illustrate the intended Morlet workflow, including baseline correction, event time zero, time-frequency ROI summaries, and cluster-aware statistics before production enablement.'),
    'pac': t(Path('caption_pac_preview.txt'), 'PAC/CFC preview output. Synthetic comodulogram and phase-binned gamma amplitude demonstrate expected reporting: frequency ranges, modulation index, surrogate p-values, and warnings about edge artifacts and multiple comparisons.'),
    'connectivity': t(Path('caption_connectivity_preview.txt'), 'Connectivity preview output. Alpha-band wPLI matrix and thresholded network graph demonstrate expected edge tables, thresholding transparency, and controls required before turning this into a production V01 workflow.'),
}

summary_paths = {
    'qc': j(Path('summary_qc.json'), {
        'status': 'enabled_v01_static_demo',
        'subjects': len(subs),
        'mean_rejected_epoch_percent': round(float(qc['rejected_epoch_percent'].mean()), 3),
        'review_subjects': qc.loc[qc['qc_status'] == 'review', 'subject'].tolist(),
        'checks': ['readability', 'sampling_rate', 'duration', 'eeg_channels', 'flat_channels', 'extreme_amplitude', 'bad_channels', 'rejected_epochs', 'ica_components'],
    }),
    'psd': j(Path('summary_psd.json'), {
        'status': 'enabled_v01_static_demo',
        'subjects': len(subs),
        'alpha_reactivity_db_mean': round(float(df['alpha_reactivity_db'].mean()), 3),
        'bands': ['delta', 'theta', 'alpha', 'beta', 'low_gamma'],
        'statistical_unit': 'subject',
    }),
    'erp': j(Path('summary_erp.json'), {
        'status': 'enabled_v01_static_demo',
        'subjects': len(subs),
        'events_total': len(ev),
        'event_id': {'standard': 1, 'target': 2},
        'p300_difference_uv_mean': round(float(df['difference_p300_uv'].mean()), 3),
        'statistical_unit': 'subject',
    }),
    'tfr': j(Path('summary_tfr_preview.json'), {'status': 'preview_not_enabled_in_v01', 'reason': 'Requires production wavelet, baseline and cluster-statistics policy.'}),
    'pac': j(Path('summary_pac_preview.json'), {'status': 'preview_not_enabled_in_v01', 'reason': 'Requires surrogate model, boundary control and multiple-comparison correction.'}),
    'connectivity': j(Path('summary_connectivity_preview.json'), {'status': 'preview_not_enabled_in_v01', 'reason': 'Requires leakage control, threshold policy and null testing.'}),
}

modules = {
    'qc': {
        'slug': 'qc',
        'page': 'qc.html',
        'title': 'QC 数据质量控制',
        'subtitle': '读取、完整性、通道、伪迹与可分析性审查',
        'status': 'V01 已启用',
        'statusLevel': 'enabled',
        'scenario': '研究助理上传 EDF/FIF 后，先判断数据是否值得继续分析，并导出给 PI 的质控说明。',
        'mneObjects': ['mne.io.Raw', 'mne.Annotations', 'Raw.plot', 'metadata summary'],
        'inputs': ['EEG 原始文件：EDF/BDF/FIF/BrainVision/SET/CNT', '采样率、通道表、事件标记或注释', '坏道和伪迹阈值', '任务范式和预处理上下文'],
        'controls': ['文件格式', '最低采样率', '最短时长', '坏道阈值', '极端振幅阈值'],
        'outputs': ['QC summary JSON', 'subject-level QC CSV', '原始片段预览图', '方法说明与复现参数', '下一步是否允许 PSD/ERP 的建议'],
        'risks': ['QC 只能提示风险，不能替代人工复核。', '眼动/肌电/电极松动需要结合实验记录判断。'],
        'figures': [
            {'label': 'Publication QC dashboard', 'src': url(FIG / 'qc-dashboard-publication.png'), 'alt': 'QC publication dashboard'},
            {'label': 'Raw trace preview', 'src': url(FIG / 'analysis-raw-segment.png'), 'alt': 'Raw trace preview'},
        ],
        'tables': [
            {'label': '受试者 QC 表', 'src': url(TAB / 'qc_subject_summary.csv')},
        ],
        'docs': [
            {'label': '参数 JSON', 'src': url(REP / 'parameters_qc.json'), 'type': 'json'},
            {'label': '方法说明', 'src': url(REP / 'methods_qc.txt'), 'type': 'text'},
            {'label': '图注', 'src': url(REP / 'caption_qc.txt'), 'type': 'text'},
            {'label': '总结 JSON', 'src': url(REP / 'summary_qc.json'), 'type': 'json'},
        ],
        'package': url(PKG / 'qc_static_research_package.zip'),
    },
    'psd': {
        'slug': 'psd',
        'page': 'psd.html',
        'title': 'PSD 静息态频谱 / 频段功率',
        'subtitle': 'Welch 功率谱、频段汇总、alpha reactivity 与 topomap',
        'status': 'V01 已启用',
        'statusLevel': 'enabled',
        'scenario': '静息态睁眼/闭眼范式，需要快速确认 alpha 峰、频段功率、受试者级统计表和投稿图。',
        'mneObjects': ['mne.io.Raw', 'Raw.compute_psd', 'mne.time_frequency.Spectrum', 'mne.viz.plot_topomap'],
        'inputs': ['连续 EEG 或静息态分段', '条件标签：eyes open / eyes closed / baseline', '参考、滤波、notch 与坏道策略', '频段定义'],
        'controls': ['频率范围', 'Welch window', '频段定义', '参考方式', '是否输出 channel-level 表'],
        'outputs': ['Welch PSD 曲线图', 'band_power CSV', 'alpha topomap', 'subject-level paired statistics', '方法、参数、软件版本与结果包'],
        'risks': ['个体 alpha 峰可能偏移，固定 8-13 Hz 需谨慎解释。', 'PSD 对参考、眼动、肌电和坏段高度敏感。'],
        'figures': [
            {'label': 'PSD publication figure', 'src': url(FIG / 'psd-bandpower-publication.png'), 'alt': 'PSD publication figure'},
            {'label': 'Alpha topomap', 'src': url(FIG / 'analysis-source.png'), 'alt': 'Alpha topography preview'},
        ],
        'tables': [
            {'label': '频段功率长表', 'src': url(TAB / 'psd_bandpower_long_format.csv')},
            {'label': '统计摘要', 'src': url(TAB / 'statistics_summary_subject_level.csv')},
        ],
        'docs': [
            {'label': '参数 JSON', 'src': url(REP / 'parameters_psd.json'), 'type': 'json'},
            {'label': '方法说明', 'src': url(REP / 'methods_psd.txt'), 'type': 'text'},
            {'label': '图注', 'src': url(REP / 'caption_psd.txt'), 'type': 'text'},
            {'label': '总结 JSON', 'src': url(REP / 'summary_psd.json'), 'type': 'json'},
        ],
        'package': url(PKG / 'psd_static_research_package.zip'),
    },
    'erp': {
        'slug': 'erp',
        'page': 'erp.html',
        'title': 'ERP 事件相关电位 / P300',
        'subtitle': '事件映射、Epoch、baseline、Evoked、成分窗口与 topomap',
        'status': 'V01 已启用',
        'statusLevel': 'enabled',
        'scenario': 'Oddball P300 客户需要确认事件、epoch 设置、P300 量化、差异波和可投稿图。',
        'mneObjects': ['mne.events_from_annotations', 'mne.Epochs', 'mne.Evoked', 'mne.viz.plot_compare_evokeds', 'mne.viz.plot_topomap'],
        'inputs': ['带注释/事件的 EEG 文件', 'event_id 映射：standard=1, target=2', 'epoch: -200 至 800 ms', 'baseline: -200 至 0 ms', 'ROI 通道与成分时间窗'],
        'controls': ['事件映射', 'epoch 起止', 'baseline', 'amplitude rejection', 'ROI 通道', '成分时间窗'],
        'outputs': ['每条件 Evoked 波形', 'target-standard 差异与窗口指标', 'ERP metrics CSV', 'topomap 与图注', '事件/epoch/QC 复现记录'],
        'risks': ['事件码含义必须由实验脚本或研究者确认。', '不能把 trial 当作独立统计单位；统计应以 subject 为单位。'],
        'figures': [
            {'label': 'ERP publication figure', 'src': url(FIG / 'erp-grand-average-publication.png'), 'alt': 'ERP publication figure'},
            {'label': 'ERP main figure', 'src': url(FIG / 'publication-main-figure.png'), 'alt': 'ERP main figure'},
        ],
        'tables': [
            {'label': 'ERP 成分指标表', 'src': url(TAB / 'erp_component_metrics.csv')},
            {'label': '统计摘要', 'src': url(TAB / 'statistics_summary_subject_level.csv')},
        ],
        'docs': [
            {'label': '参数 JSON', 'src': url(REP / 'parameters_erp.json'), 'type': 'json'},
            {'label': '方法说明', 'src': url(REP / 'methods_erp.txt'), 'type': 'text'},
            {'label': '图注', 'src': url(REP / 'caption_erp.txt'), 'type': 'text'},
            {'label': '总结 JSON', 'src': url(REP / 'summary_erp.json'), 'type': 'json'},
        ],
        'package': url(PKG / 'erp_static_research_package.zip'),
    },
    'tfr': {
        'slug': 'tfr',
        'page': 'tfr.html',
        'title': 'TFR / ERSP / ITC 时频分析预研页',
        'subtitle': 'Morlet 小波设计、baseline、ERSP、ITC、cluster 统计',
        'status': 'V01 预研，尚未启用',
        'statusLevel': 'preview',
        'scenario': 'ASSR、Stroop、运动想象等范式需要时频功率和锁相指标；本页用于确认科研交互和输出合同。',
        'mneObjects': ['mne.time_frequency.tfr_morlet', 'Epochs', 'AverageTFR', 'cluster permutation design'],
        'inputs': ['事件锁定 epochs', '频率列表与 n_cycles', 'baseline 区间和校正方式', '输出指标：power / ITC', 'ROI、时间窗和多重比较策略'],
        'controls': ['频率范围', 'n_cycles', 'baseline mode', 'decimation', 'ROI', 'cluster p 阈值'],
        'outputs': ['ERSP heatmap', 'ITC 曲线', 'ROI summary CSV', '统计掩膜/cluster 表', '方法说明、参数和预研结果包'],
        'risks': ['V01 不应直接启用：需要先固化 wavelet 参数、baseline 策略、cluster 统计和伪迹控制。', '过度平滑和多重比较会影响科研结论。'],
        'figures': [
            {'label': 'TFR preview chart', 'src': url(FIG / 'tfr-ersp-itc-preview-publication.png'), 'alt': 'TFR preview chart'},
            {'label': 'Time-frequency reference', 'src': url(FIG / 'analysis-timefreq.png'), 'alt': 'Time-frequency reference'},
        ],
        'tables': [
            {'label': 'TFR ROI 预览表', 'src': url(TAB / 'tfr_roi_summary_preview.csv')},
        ],
        'docs': [
            {'label': '参数 JSON', 'src': url(REP / 'parameters_tfr.json'), 'type': 'json'},
            {'label': '方法说明', 'src': url(REP / 'methods_tfr_preview.txt'), 'type': 'text'},
            {'label': '图注', 'src': url(REP / 'caption_tfr_preview.txt'), 'type': 'text'},
            {'label': '总结 JSON', 'src': url(REP / 'summary_tfr_preview.json'), 'type': 'json'},
        ],
        'package': url(PKG / 'tfr_static_research_package.zip'),
    },
    'pac': {
        'slug': 'pac',
        'page': 'pac.html',
        'title': 'PAC / CFC 相位-振幅耦合预研页',
        'subtitle': 'theta phase × gamma amplitude、comodulogram、surrogate 检验',
        'status': 'V01 预研，尚未启用',
        'statusLevel': 'preview',
        'scenario': '麻醉苏醒、睡眠、记忆任务等客户可能关注 cross-frequency coupling；本页先定义完整输入输出与审稿风险。',
        'mneObjects': ['Raw/Epochs filtering', 'Hilbert transform design', 'surrogate/null model', 'comodulogram report'],
        'inputs': ['连续或事件锁定 EEG', 'phase frequency range', 'amplitude frequency range', '滤波阶数/边界处理', 'surrogate 生成策略', 'ROI 和统计校正方案'],
        'controls': ['相位频段', '振幅频段', 'filter length', 'Hilbert 边界裁剪', 'surrogate 次数', 'FDR/cluster 校正'],
        'outputs': ['comodulogram', 'phase-binned amplitude plot', 'modulation index table', 'surrogate p-values', '方法与风险说明'],
        'risks': ['PAC 极易受滤波、边界、波形非正弦和伪迹影响。', '必须有 surrogate/null model 和多重比较控制后才适合生产启用。'],
        'figures': [
            {'label': 'PAC preview chart', 'src': url(FIG / 'pac-comodulogram-preview-publication.png'), 'alt': 'PAC preview chart'},
            {'label': 'ICA component reference', 'src': url(FIG / 'analysis-ica.png'), 'alt': 'ICA reference preview'},
        ],
        'tables': [
            {'label': 'PAC/CFC 预览表', 'src': url(TAB / 'pac_cfc_summary_preview.csv')},
        ],
        'docs': [
            {'label': '参数 JSON', 'src': url(REP / 'parameters_pac.json'), 'type': 'json'},
            {'label': '方法说明', 'src': url(REP / 'methods_pac_preview.txt'), 'type': 'text'},
            {'label': '图注', 'src': url(REP / 'caption_pac_preview.txt'), 'type': 'text'},
            {'label': '总结 JSON', 'src': url(REP / 'summary_pac_preview.json'), 'type': 'json'},
        ],
        'package': url(PKG / 'pac_static_research_package.zip'),
    },
    'connectivity': {
        'slug': 'connectivity',
        'page': 'connectivity.html',
        'title': 'Connectivity 连接性预研页',
        'subtitle': 'coherence / PLV / wPLI、矩阵、网络图与边表',
        'status': 'V01 预研，尚未启用',
        'statusLevel': 'preview',
        'scenario': '静息态或任务态网络分析客户需要透明的边定义、阈值、矩阵、网络图和可复查边表。',
        'mneObjects': ['Epochs/Raw spectral connectivity design', 'coherence', 'PLV', 'wPLI', 'graph summary'],
        'inputs': ['连续或分段 EEG', '频段定义', '连接性指标：coherence/PLV/wPLI', '参考和体积传导控制', '阈值策略', '节点/ROI 定义'],
        'controls': ['metric', 'frequency band', 'window length', 'threshold', 'ROI/node set', 'null model'],
        'outputs': ['connectivity matrix', 'thresholded network graph', 'edge table CSV', 'graph metrics', '参数、方法和预研结果包'],
        'risks': ['参考方式与体积传导会显著影响连接性。', '网络阈值需要预注册或敏感性分析，不能只保留好看的边。'],
        'figures': [
            {'label': 'Connectivity preview chart', 'src': url(FIG / 'connectivity-network-preview-publication.png'), 'alt': 'Connectivity preview chart'},
            {'label': 'Scalp/source reference', 'src': url(FIG / 'analysis-source.png'), 'alt': 'Source reference preview'},
        ],
        'tables': [
            {'label': '连接边表预览', 'src': url(TAB / 'connectivity_edges_preview.csv')},
        ],
        'docs': [
            {'label': '参数 JSON', 'src': url(REP / 'parameters_connectivity.json'), 'type': 'json'},
            {'label': '方法说明', 'src': url(REP / 'methods_connectivity_preview.txt'), 'type': 'text'},
            {'label': '图注', 'src': url(REP / 'caption_connectivity_preview.txt'), 'type': 'text'},
            {'label': '总结 JSON', 'src': url(REP / 'summary_connectivity_preview.json'), 'type': 'json'},
        ],
        'package': url(PKG / 'connectivity_static_research_package.zip'),
    },
}

manifest = {
    'generatedAt': '2026-06-18',
    'product': 'QLanalyser Online v0.1 Pilot',
    'purpose': 'Standalone static research-module pages for customer testing and scientific UI review.',
    'researchGuardrail': 'All displayed data are synthetic and for research workflow testing only; not for clinical diagnosis.',
    'sampleData': {
        'metadata': '/' + meta,
        'events_tsv': url(OUT / 'data' / 'synthetic_events.tsv'),
        'raw_preview_csv': url(OUT / 'data' / 'synthetic_raw_preview_8ch_12s.csv'),
        'subject_metrics_csv': url(TAB / 'synthetic_subject_level_metrics.csv'),
        'source_edf': url(ROOT / 'frontend' / 'assets' / 'teaching_oddball.edf'),
        'source_events': url(ROOT / 'frontend' / 'assets' / 'teaching_oddball_events.tsv'),
    },
    'shared': {
        'mne_reference': mne_reference,
        'reviewer_checklist': reviewer_checklist,
        'figure_background': url(FIG / 'qlanalyser-neuron-firing-bg.png'),
    },
    'modules': modules,
}
manifest_path = j(Path('research_module_manifest.json'), manifest)


# Build per-module ZIP packages and an all-in-one package for tomorrow's manual testing.
for slug, module in modules.items():
    package_path = PKG / f'{slug}_static_research_package.zip'
    with zipfile.ZipFile(package_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for fig in module.get('figures', []):
            src = ROOT / 'frontend' / fig['src'].lstrip('/')
            if src.exists():
                zf.write(src, arcname=src.relative_to(OUT).as_posix() if OUT in src.parents else src.relative_to(ROOT / 'frontend').as_posix())
        for table in module.get('tables', []):
            src = ROOT / 'frontend' / table['src'].lstrip('/')
            if src.exists():
                zf.write(src, arcname=src.relative_to(OUT).as_posix())
        for doc in module.get('docs', []):
            src = ROOT / 'frontend' / doc['src'].lstrip('/')
            if src.exists():
                zf.write(src, arcname=src.relative_to(OUT).as_posix())
        for shared in [mne_reference, reviewer_checklist, subject_csv, events_tsv, raw_csv, stats_csv]:
            src = ROOT / 'frontend' / shared
            if src.exists():
                zf.write(src, arcname=src.relative_to(OUT).as_posix())
    module['package'] = url(package_path)

manifest['modules'] = modules
manifest_path = j(Path('research_module_manifest.json'), manifest)
all_package = PKG / 'qlanalyser_research_modules_static_test_package.zip'
with zipfile.ZipFile(all_package, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for item in OUT.rglob('*'):
        if item.is_file() and item != all_package:
            zf.write(item, arcname=item.relative_to(OUT).as_posix())
print(json.dumps({'ok': True, 'manifest': '/' + manifest_path, 'all_package': url(all_package), 'modules': list(modules)}, ensure_ascii=False, indent=2))

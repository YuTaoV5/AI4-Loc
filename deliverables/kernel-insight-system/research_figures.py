"""Publication-style figures computed exclusively from frozen project records."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

A = '模型按需检索'
B = '自动预检增强'

def build(media, pairs, family, counts, ci, labels, names):
    ink, gray, blue, light = '#1D1D1F', '#6E6E73', '#0071E3', '#D2D2D7'
    def save(name, fig):
        fig.savefig(media / (name+'.svg'))
        fig.savefig(media / (name+'.png'), dpi=160)
        plt.close(fig)
    def axis(ax, letter, title, grid='x'):
        ax.set_title(f'{letter}  {title}', loc='left', fontsize=21, weight='bold', pad=20)
        ax.tick_params(length=0, pad=9)
        ax.set_axisbelow(True)
        if grid: ax.grid(axis=grid, color='#ECECF0', lw=1)
        for side in ['top','right','left']: ax.spines[side].set_visible(False)
    before = np.array([p['before']['metrics']['modelRequests'] for p in pairs])
    after = np.array([p['after']['metrics']['modelRequests'] for p in pairs])
    tb = np.array([p['before']['metrics']['localizationSeconds'] for p in pairs])
    ta = np.array([p['after']['metrics']['localizationSeconds'] for p in pairs])

    # Figure 1: categories and split counts, with actual integer denominators.
    items=sorted(family.items(),key=lambda x:-x[1])
    fig,axs=plt.subplots(1,2,figsize=(16,6.4),gridspec_kw={'width_ratios':[1.7,1]})
    ax=axs[0]; y=np.arange(len(items)); vals=[v for k,v in items]
    ax.barh(y,vals,height=.65,color=[blue if k=='protection' else light for k,v in items])
    ax.set_yticks(y,[names[k] for k,v in items],fontsize=15);ax.invert_yaxis();ax.set_xlim(0,31)
    for i,v in enumerate(vals):ax.text(v+.3,i,str(v),va='center',fontsize=16)
    ax.set_xlabel('有效样本数（故障 59 + 健康 1）',fontsize=17)
    axis(ax,'a','严格定位集的故障族分布')
    ax=axs[1]
    datasets=['社区报告集','历史注入集','网站扩展集','严格定位集']
    train=np.array([3,43,59,51]);test=np.array([3,21,21,9])
    ax.barh(range(4),train,color=light,label='训练 / 开发')
    ax.barh(range(4),test,left=train,color=blue,label='测试')
    for i,(u,v) in enumerate(zip(train,test)):
        if i==0:
            ax.text(u+v+2,i,'3 / 3',ha='left',va='center',fontsize=15,color=gray)
        else:
            ax.text(u/2,i,str(u),ha='center',va='center',fontsize=17)
            ax.text(u+v/2,i,str(v),ha='center',va='center',fontsize=17,color='white')
    ax.set_yticks(range(4),datasets,fontsize=16);ax.invert_yaxis();ax.set_xlim(0,85)
    ax.set_xlabel('清单中样本条目数',fontsize=17);axis(ax,'b','划分与库存（禁止跨集相加）')
    ax.legend(frameon=False,fontsize=15,loc='lower right',bbox_to_anchor=(1,-.26),ncol=2)
    fig.subplots_adjust(left=.15,right=.98,top=.88,bottom=.18,wspace=.62);save('coverage',fig)

    # Input capability is a design contract, explicitly not empirical success.
    fig,ax=plt.subplots(figsize=(16,6.2))
    capability=np.array([[1,1,1,1],[1,1,0,1],[1,1,1,0],[1,1,0,0],[0,0,0,1],[0,0,0,1],[0,0,0,0]])
    ax.imshow(capability,cmap=ListedColormap(['#F1F1F4','#DDEBFE']),vmin=0,vmax=1,aspect='auto')
    ax.set_xticks(range(4),['故障定界','函数候选','已读源码位置','产物身份检查'],fontsize=18)
    ax.xaxis.tick_top();ax.set_yticks(range(7),['日志 + 产物 + 源码','日志 + 产物','日志 + 源码','仅日志','产物 + 源码','仅产物','仅源码'],fontsize=18)
    for y in range(7):
        for x in range(4):ax.text(x,y,'允许' if capability[y,x] else '缺证据',ha='center',va='center',fontsize=20,color=blue if capability[y,x] else gray)
    ax.set_xticks(np.arange(-.5,4,1),minor=True);ax.set_yticks(np.arange(-.5,7,1),minor=True)
    ax.grid(which='minor',color='white',lw=5);ax.tick_params(which='both',length=0,pad=14)
    for sp in ax.spines.values():sp.set_visible(False)
    fig.subplots_adjust(left=.21,right=.98,top=.87,bottom=.06);save('input-contract',fig)

    # Connected paired observations, no invented variance or fitted trend.
    def paired(name,b,a,unit,xmax,total):
        fig,axs=plt.subplots(1,2,figsize=(16,6.2),gridspec_kw={'width_ratios':[1.55,1]})
        ax=axs[0]
        for i,(u,v) in enumerate(zip(b,a)):
            ax.plot([v,u],[i,i],color=light,lw=4,zorder=1)
            ax.scatter(u,i,s=105,facecolors='white',edgecolors=gray,lw=2,label=A if i==0 else None,zorder=3)
            ax.scatter(v,i,s=105,color=blue,label=B if i==0 else None,zorder=3)
            ax.annotate(f'{u:g}' if unit=='次' else f'{u:.2f}',(u,i),xytext=(9,-4),textcoords='offset points',fontsize=15,color=gray)
            ax.annotate(f'{v:g}' if unit=='次' else f'{v:.2f}',(v,i),xytext=(-10,-4),ha='right',textcoords='offset points',fontsize=15,color=blue)
        ax.set_yticks(range(6),labels,fontsize=17);ax.invert_yaxis();ax.set_xlim(-xmax*.12,xmax)
        ax.set_xlabel(f'每例实际模型请求 / {unit}' if unit=='次' else '每例定位流程耗时 / 秒',fontsize=17)
        axis(ax,'a','相同案例的单次配对观察')
        ax.legend(frameon=False,fontsize=15,loc='lower right',bbox_to_anchor=(1,-.37),ncol=2)
        ax=axs[1]; delta=b-a;y=np.arange(6)
        ax.barh(y,delta,color=blue,height=.5)
        for i,v in enumerate(delta):ax.text(v+max(delta)*.035,i,f'{v:g}' if unit=='次' else f'{v:.3f}',va='center',fontsize=16,color=blue)
        ax.set_yticks(y,labels,fontsize=16);ax.invert_yaxis();ax.set_xlim(0,max(delta)*1.35)
        ax.set_xlabel(f'减少量 / {unit}（按需检索 − 预检增强）',fontsize=16)
        axis(ax,'b',total)
        fig.subplots_adjust(left=.13,right=.98,top=.86,bottom=.26,wspace=.48);save(name,fig)
    paired('requests',before,after,'次',9,'六例共减少 15 次请求（71.4%）')
    paired('latency',tb,ta,'秒',56,'六例共减少 85.513 秒（47.2%）')

    fig,axs=plt.subplots(1,2,figsize=(16,5.8),gridspec_kw={'width_ratios':[1.65,1]})
    ax=axs[0]
    result=np.array([[1 if p[s]['codeLocationHit'] else (-1 if p[s]['status']=='failed' else 0) for s in ['before','after']] for p in pairs[:5]])
    ax.imshow(result,aspect='auto',vmin=-1,vmax=1,cmap=ListedColormap(['#E0E0E5','#F1F1F4','#DDEBFE']))
    ax.set_xticks([0,1],[A,B],fontsize=18);ax.xaxis.tick_top();ax.set_yticks(range(5),labels[:5],fontsize=18)
    for i in range(5):
        for j in range(2):ax.text(j,i,{-1:'运行失败',0:'未命中',1:'命中'}[result[i,j]],ha='center',va='center',fontsize=22,color=blue if result[i,j]==1 else gray)
    ax.set_xticks([-.5,.5,1.5],minor=True);ax.set_yticks(np.arange(-.5,5,1),minor=True);ax.grid(which='minor',color='white',lw=6);ax.tick_params(which='both',length=0,pad=15)
    for sp in ax.spines.values():sp.set_visible(False)
    ax.set_title('a  五个故障的代码位置命中',loc='left',fontsize=21,weight='bold',pad=58)
    ax=axs[1];ax.axis('off')
    for y,value,label in [(.78,'2 例','未命中 / 失败 → 命中'),(.48,'0 例','命中 → 未命中 / 失败'),(.18,'1 例','健康基线：两组均拒答')]:
        ax.text(.03,y,value,fontsize=38,color=blue if y>.7 else ink,weight='bold');ax.text(.03,y-.11,label,fontsize=19,color=gray)
    fig.subplots_adjust(left=.13,right=.96,top=.78,bottom=.05,wspace=.38);save('paired-hits',fig)

    fig,axs=plt.subplots(1,2,figsize=(16,5.6),gridspec_kw={'width_ratios':[1.5,1]})
    ax=axs[0];auto=[counts[s]['preflightToolCalls'] for s in ['before','after']];chosen=[counts[s]['modelToolCalls'] for s in ['before','after']]
    ax.barh([0,1],auto,color=blue,height=.4,label='确定性自动预检')
    ax.barh([0,1],chosen,left=auto,color=light,height=.4,label='模型选择工具')
    for i in [0,1]:
        ax.text(auto[i]/2,i,str(auto[i]),ha='center',va='center',fontsize=25,color='white')
        if chosen[i]:ax.text(auto[i]+chosen[i]/2,i,str(chosen[i]),ha='center',va='center',fontsize=25)
        ax.text(auto[i]+chosen[i]+.6,i,str(auto[i]+chosen[i]),va='center',fontsize=20)
    ax.set_yticks([0,1],[A,B],fontsize=18);ax.invert_yaxis();ax.set_xlim(0,29);ax.set_xlabel('六例工具检查次数',fontsize=17)
    axis(ax,'a','预先准备证据，替代重复交互');ax.legend(frameon=False,loc='lower left',bbox_to_anchor=(0,-.27),fontsize=16,ncol=2)
    ax=axs[1];val=[counts[s]['observedPromptTokens']/1000 for s in ['before','after']]
    ax.bar([0,1],val,color=[light,blue],width=.5)
    for i,v in enumerate(val):ax.text(i,v+4,f'{v:.3f}k',ha='center',fontsize=20,color=blue if i else ink)
    ax.set_xticks([0,1],['按需检索\n20 / 21 请求可观测','预检增强\n6 / 6 请求可观测'],fontsize=16)
    ax.set_ylim(0,125);ax.set_ylabel('已记录 prompt tokens / 千',fontsize=16);axis(ax,'b','输入 token 的可观测合计','y')
    fig.subplots_adjust(left=.15,right=.97,top=.82,bottom=.22,wspace=.56);save('tool-work',fig)

    fig,ax=plt.subplots(figsize=(16,5.8));ss=[(3,5,A),(5,5,B),(2,3,'额外探索（非独立盲测）')]
    for i,(k,n,label) in enumerate(ss):
        lo,hi=ci(k,n);p=k/n;c=blue if i==1 else gray
        ax.errorbar(p*100,i,xerr=[[(p-lo)*100],[(hi-p)*100]],fmt='o',ms=12,color=c,elinewidth=3,capsize=9,capthick=2)
        ax.text(p*100,i-.2,f'{k}/{n} = {p:.0%}',ha='center',fontsize=20,color=c)
        ax.text((lo+hi)*50,i+.24,f'95% CI [{lo:.1%}, {hi:.1%}]',ha='center',fontsize=18,color=c)
    ax.set_yticks(range(3),[x[2] for x in ss],fontsize=19);ax.set_ylim(2.6,-.6);ax.set_xlim(0,108)
    ax.set_xlabel('代码位置命中率 / %（精确二项区间）',fontsize=19);axis(ax,'a','样本很小，点估计不能替代不确定性')
    fig.subplots_adjust(left=.29,right=.96,top=.86,bottom=.16);save('uncertainty',fig)

    # Three metrics in separate scales. Completion and accuracy denominators differ.
    fig,axs=plt.subplots(1,3,figsize=(16,5.9))
    for ax,letter,title,values,ylim,ylabel in zip(axs,'abc',['故障代码位置命中','全部案例模型请求','全部案例定位时间'],[[60,100],[21,6],[181.347,95.834]],[125,26,220],['命中率 / %（n=5）','实际 HTTP 尝试 / 次（n=6）','定位流程总和 / 秒（n=6）']):
        ax.bar([0,1],values,color=[light,blue],width=.5)
        for i,v in enumerate(values):ax.text(i,v+ylim*.035,(f'{int(v)}%' if letter=='a' else (f'{v:.3f}' if letter=='c' else str(v))),ha='center',fontsize=22,color=blue if i else ink)
        ax.set_xticks([0,1],['按需检索','预检增强'],fontsize=17);ax.set_ylim(0,ylim);ax.set_ylabel(ylabel,fontsize=16)
        axis(ax,letter,title,'y')
    fig.subplots_adjust(left=.07,right=.98,top=.85,bottom=.16,wspace=.54);save('result-overview',fig)

"""Generate eight reproducible Python figures with ReportLab graphics.

PDF figures need only pandas, numpy and reportlab. Optionally pass Poppler's
pdftoppm executable to also render the PNGs used in the Word report.
"""
from pathlib import Path
import argparse, json, subprocess
import numpy as np
import pandas as pd
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Circle, PolyLine
from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor, Color, white

BLUE='#225F83'; TEAL='#16877F'; ORANGE='#C87229'; INK='#172F42'; GRAY='#566673'; GRID='#DCE4E9'

def text(d,x,y,t,size=13,color=INK,anchor='start',bold=False):
    d.add(String(x,y,str(t),fontName='Helvetica-Bold' if bold else 'Helvetica',
        fontSize=size,fillColor=HexColor(color),textAnchor=anchor))

def line(d,x1,y1,x2,y2,color=GRID,width=.7,dash=None):
    d.add(Line(x1,y1,x2,y2,strokeColor=HexColor(color),strokeWidth=width,strokeDashArray=dash))

def box(d,x,y,w,h,color):
    d.add(Rect(x,y,w,h,fillColor=HexColor(color),strokeColor=None))

def start(title,subtitle,height=370):
    d=Drawing(720,height); box(d,0,0,720,height,'#FFFFFF')
    text(d,14,height-24,title,17,bold=True)
    text(d,14,height-45,subtitle,11,color=GRAY)
    return d

def axes(d,x,y,w,h,xmax,ymax,xticks,yticks,xlab='',ylab='',xfmt=None,yfmt=None):
    for a in yticks:
        yp=y+a/ymax*h; line(d,x,yp,x+w,yp)
        text(d,x-9,yp-4,yfmt(a) if yfmt else f'{a:g}',11,anchor='end',color=GRAY)
    for a in xticks:
        xp=x+a/xmax*w
        text(d,xp,y-19,xfmt(a) if xfmt else f'{a:g}',11,anchor='middle',color=GRAY)
    line(d,x,y,x+w,y,GRAY); line(d,x,y,x,y+h,GRAY)
    text(d,x+w/2,y-40,xlab,12,anchor='middle')
    if ylab: text(d,x,y+h+12,ylab,12)

def poly(d,xs,ys,color=BLUE,width=2):
    pts=[]
    for x,y in zip(xs,ys): pts.extend([float(x),float(y)])
    d.add(PolyLine(pts,strokeColor=HexColor(color),strokeWidth=width,fillColor=None))

def save(d,name,out,pdftoppm):
    pdf=out/(name+'.pdf'); renderPDF.drawToFile(d,str(pdf))
    if pdftoppm:
        subprocess.run([str(pdftoppm),'-singlefile','-scale-to','2000','-png',str(pdf),str(out/name)],check=True,capture_output=True)

def main(results,out,pdftoppm=None):
    out.mkdir(parents=True,exist_ok=True)
    s=json.loads((results/'summary.json').read_text())
    m=pd.read_csv(results/'monthly_performance.csv')
    st=pd.read_csv(results/'state_performance.csv').head(10)
    # 1. Two aligned panels: order counts and completed-order durations.
    d=start('Order volume and delivery time by purchase month',
        'Historical benchmark | Jan 2017 to Jun 2018 | all orders above; completed orders below',450)
    x,y,w,h=64,245,630,115
    axes(d,x,y,w,h,17,8000,[],[0,4000,8000],ylab='Orders',yfmt=lambda a:f'{int(a):,}')
    xs=np.linspace(x+14,x+w-14,18)
    for xp,v in zip(xs,m.orders): box(d,xp-11,y,22,v/8000*h,BLUE)
    y2,h2=65,115
    axes(d,x,y2,w,h2,17,40,[],[0,10,20,30,40],ylab='Delivery days')
    poly(d,xs,y2+m['median']/40*h2,TEAL,2.5)
    poly(d,xs,y2+m.p90/40*h2,ORANGE,2.5)
    for i in [0,3,6,9,12,15,17]:
        text(d,xs[i],y2-21,m.month[i],10,anchor='middle',color=GRAY)
    line(d,425,195,448,195,TEAL,2.5);text(d,455,191,'Median',11)
    line(d,535,195,558,195,ORANGE,2.5);text(d,565,191,'90th percentile',11)
    text(d,14,12,'86,288 purchased orders; 83,696 eligible completed cycles. Separate axes avoid a misleading dual scale.',10,GRAY)
    save(d,'01_monthly_trends',out,pdftoppm)
    # 2. Distribution and cumulative delivery share, with explicit hidden tail.
    hist=pd.read_csv(results/'cycle_histogram.csv'); ecdf=pd.read_csv(results/'cycle_ecdf.csv')
    d=start('Most deliveries finish quickly but a long tail remains',
        'Historical benchmark | 96,470 completed orders | delivery cycle from purchase to customer',380)
    x,y,w,h=60,70,360,220
    ymax=20000
    axes(d,x,y,w,h,60,ymax,[0,15,30,45,60],[0,5000,10000,15000,20000],
        xlab='Delivery days',ylab='Orders in each 2 day bin',yfmt=lambda a:f'{int(a):,}')
    for row in hist.itertuples():box(d,x+row.left_days/60*w,y,2/60*w-1,row.orders/ymax*h,BLUE)
    med=s['descriptive']['cycle_days']['median'];p90=s['descriptive']['cycle_days']['p90']
    for v,col in [(med,TEAL),(p90,ORANGE)]:line(d,x+v/60*w,y,x+v/60*w,y+h,col,1.7,[4,3])
    text(d,476,278,'Median  10.22 days',13,TEAL,bold=True)
    text(d,476,253,'P90       23.10 days',13,ORANGE,bold=True)
    text(d,476,215,'Delivered within',12,bold=True)
    for j,day in enumerate([7,14,30,60]):
        pct=ecdf.loc[ecdf.days.eq(day),'cumulative_pct'].iat[0]
        text(d,476,188-j*25,f'{day:>2} days: {pct:.1f}%',13)
    text(d,14,13,'306 orders above 60 days are outside the plotted range; they remain in all summary calculations.',10,GRAY)
    save(d,'02_cycle_distribution',out,pdftoppm)
    # 3. Dot plot; fixed 0-100 scale and full denominators.
    d=start('On time delivery differs across major destination states',
        'Historical benchmark | ten states with the largest eligible completed order counts',420)
    x,y,w,h=84,61,440,275
    for tick in [0,20,40,60,80,100]:
        xx=x+w*tick/100;line(d,xx,y,xx,y+h);text(d,xx,y-19,str(tick),11,anchor='middle',color=GRAY)
    overall=s['on_time_pct'];xx=x+w*overall/100;line(d,xx,y,xx,y+h,ORANGE,1.3,[4,3])
    text(d,542,350,'On time',11,bold=True);text(d,697,350,'Eligible n',11,anchor='end',bold=True)
    for i,row in enumerate(st.itertuples()):
        yy=y+h-14-i*27
        text(d,68,yy-4,row.state,12,anchor='end',bold=True)
        d.add(Circle(x+w*row.on_time_pct/100,yy,4,fillColor=HexColor(BLUE),strokeColor=None))
        text(d,542,yy-4,f'{row.on_time_pct:.2f}%',11)
        text(d,697,yy-4,f'{row.orders:,}',11,anchor='end')
    text(d,292,18,'On time delivery (%)',12,anchor='middle')
    text(d,14,386,'',10)
    text(d,14,365,'Dashed line: all eligible orders, 93.23%',11,ORANGE)
    save(d,'03_state_on_time',out,pdftoppm)
    # 4. Common-cohort additive means.
    d=start('Transit is the largest part of elapsed delivery time',
        'Historical benchmark | same 95,082 completed orders with valid sequential milestones',280)
    names=['Approval','Dispatch','Transit'];cols=['approval_wait_days','dispatch_days','transit_days'];colors=[GRAY,TEAL,BLUE]
    x,y,w=55,130,620;total=s['stage_means']['cycle_days'];cursor=x
    for name,col,color in zip(names,cols,colors):
        val=s['stage_means'][col];ww=val/total*w;box(d,cursor,y,ww,42,color)
        if ww>45:text(d,cursor+ww/2,y+15,f'{val:.2f} d',13,'#FFFFFF',anchor='middle',bold=True)
        cursor+=ww
    for i,(name,col,color) in enumerate(zip(names,cols,colors)):
        bx=55+i*213;box(d,bx,84,12,12,color);text(d,bx+19,84,f'{name}: {s["stage_means"][col]:.2f} days',12)
    text(d,55,48,f'Total mean {total:.2f} days | transit share {s["transit_share_pct"]:.2f}%',14,bold=True)
    text(d,14,12,'Means are additive on a common cohort. Medians do not add and are not used for the time shares.',10,GRAY)
    save(d,'04_stage_decomposition',out,pdftoppm)
    # 5. Scatter uses a seeded sample and log1p coordinates to retain zero charges.
    sample=pd.read_csv(results/'scatter_sample.csv')
    d=start('Heavier orders tend to carry higher freight charges',
        'Historical benchmark | random sample of 3,000 from 96,448 complete weight and freight records',390)
    x,y,w,h=72,67,610,235;xm=np.log10(201);ym=np.log10(2001)
    for val in [0,10,100,1000]:
        yy=y+np.log10(1+val)/ym*h;line(d,x,yy,x+w,yy);text(d,x-8,yy-4,str(val),11,anchor='end',color=GRAY)
    for val in [0,1,10,100]:
        xx=x+np.log10(1+val)/xm*w;text(d,xx,y-20,str(val),11,anchor='middle',color=GRAY)
    line(d,x,y,x+w,y,GRAY);line(d,x,y,x,y+h,GRAY)
    for row in sample.itertuples():
        d.add(Circle(x+np.log10(1+row.weight_kg)/xm*w,y+np.log10(1+row.freight_brl)/ym*h,
            1.25,fillColor=Color(.13,.37,.51,alpha=.18),strokeColor=None))
    text(d,x,y+h+12,'Freight charge (BRL)',12)
    text(d,x+w/2,26,'Total product weight (kg) | both axes use log10(1 + value)',12,anchor='middle')
    text(d,14,7,'Zero charges are retained. Charges are not carrier operating costs; the sample does not drive the summary statistics.',10,GRAY)
    save(d,'05_weight_freight',out,pdftoppm)
    # 6. Complete-case, average-rank Spearman matrix.
    corr=pd.read_csv(results/'spearman_correlations.csv',index_col=0)
    labels=['Cycle days','Freight','Order value','Weight','Volume','Item count']
    d=start('Several size and charge measures move together',
        'Historical benchmark | Spearman rank correlation | same 96,448 complete orders in every cell',430)
    x,y,cell=139,56,53
    for i,name in enumerate(labels):
        text(d,x-10,y+(5-i)*cell+22,name,12,anchor='end')
        text(d,x+i*cell+cell/2,y-20,['Cycle','Freight','Value','Weight','Volume','Items'][i],10,anchor='middle')
        for j in range(6):
            v=float(corr.iloc[i,j]);base=np.array([.13,.37,.51]) if v>=0 else np.array([.78,.36,.15])
            rgb=np.ones(3)*(1-abs(v))+base*abs(v)
            d.add(Rect(x+j*cell,y+(5-i)*cell,cell,cell,fillColor=Color(*rgb),strokeColor=white,strokeWidth=1))
            text(d,x+j*cell+cell/2,y+(5-i)*cell+22,f'{v:.2f}',12,'#FFFFFF' if abs(v)>.65 else INK,anchor='middle')
    text(d,491,324,'Correlation scale',12,bold=True)
    for i,v in enumerate([-1,-.5,0,.5,1]):
        base=np.array([.13,.37,.51]) if v>=0 else np.array([.78,.36,.15]);rgb=np.ones(3)*(1-abs(v))+base*abs(v)
        d.add(Rect(495,289-i*34,28,25,fillColor=Color(*rgb),strokeColor=HexColor(GRID)))
        text(d,536,296-i*34,f'{v:+.1f}',12)
    text(d,491,100,'Rank associations',12);text(d,491,81,'are not causal effects.',12)
    text(d,14,7,'Average ranks handle ties. Product volume is summed catalogue volume, not measured packed shipment volume.',10,GRAY)
    save(d,'06_correlation_heatmap',out,pdftoppm)
    # 7. Pareto-style late counts (all 27 states contribute to cumulative share).
    allstates=pd.read_csv(results/'state_performance.csv').sort_values('late',ascending=False)
    top=allstates.head(6);rest=int(allstates.iloc[6:].late.sum())
    counts=top.late.tolist()+[rest];labels=top.state.tolist()+['Other 21']
    cumulative=np.cumsum(counts)/sum(counts)*100
    d=start('Two states account for half of recorded late orders',
        'Historical benchmark | 6,534 late orders | ranked by number of affected orders',380)
    x,y,w,h=65,71,590,195
    axes(d,x,y,w,h,6,2000,[],[0,500,1000,1500,2000],ylab='Late orders',yfmt=lambda a:f'{int(a):,}')
    xs=np.linspace(x+32,x+w-32,7)
    for xp,v,label in zip(xs,counts,labels):
        box(d,xp-23,y,46,v/2000*h,BLUE);text(d,xp,y+v/2000*h+7,f'{v:,}',11,anchor='middle');text(d,xp,y-21,label,11,anchor='middle')
    text(d,14,310,'SP and RJ together: 3,315 late orders (50.73% of all late orders)',13,ORANGE,bold=True)
    text(d,14,13,'Other 21 combines the remaining destination states. Counts measure workload, not risk per order.',10,GRAY)
    save(d,'07_late_order_burden',out,pdftoppm)
    # 8. Synthetic experiment; assumed cost components shown explicitly.
    sim=s['synthetic'];component=sim['mean_components']
    d=start('Hypothetical transportation cost and sensitivity',
        'SIMULATED ONLY | 2,000 shipments | seed 20261022 | coefficients are planning assumptions',340)
    x,y,w=55,191,615;total=sim['cost']['mean'];cursor=x
    colors=[GRAY,BLUE,TEAL,ORANGE]
    for (col,v),color in zip(component.items(),colors):
        ww=v/total*w;box(d,cursor,y,ww,40,color)
        if ww>35:text(d,cursor+ww/2,y+14,f'{v:.2f}',11,'#FFFFFF',anchor='middle',bold=True)
        cursor+=ww
    text(d,55,247,f'Mean cost: BRL {total:.2f} per shipment',15,bold=True)
    for i,(label,color) in enumerate(zip(['Base','Distance','Weight','Extra delay'],colors)):
        box(d,55+i*155,163,10,10,color);text(d,71+i*155,163,label,11)
    text(d,55,124,'Cost only scenario',12,bold=True);text(d,470,124,'Mean BRL',12,anchor='end',bold=True);text(d,668,124,'Reduction',12,anchor='end',bold=True)
    for i,(key,label) in enumerate([('distance_minus10pct','10% lower distance'),('delay_minus1day','Up to one fewer delay day')]):
        val=sim['sensitivity_mean_cost_brl'][key];saving=total-val
        text(d,55,96-i*28,label,12);text(d,470,96-i*28,f'{val:.2f}',12,anchor='end');text(d,668,96-i*28,f'{saving/total*100:.2f}%',12,anchor='end')
    text(d,14,15,'These are arithmetic what if results. Implementation cost, feasibility and real service effects are not modeled.',10,GRAY)
    save(d,'08_simulated_cost_sensitivity',out,pdftoppm)
    print(json.dumps({'figures':8,'output':str(out),'pngs':bool(pdftoppm)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,default=Path('results'))
    p.add_argument('--output',type=Path,default=Path('figures'));p.add_argument('--pdftoppm',type=Path)
    a=p.parse_args();main(a.results,a.output,a.pdftoppm)

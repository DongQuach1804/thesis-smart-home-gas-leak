#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sinh TOÀN BỘ hình cho slide thuyết trình theo PHIÊN BẢN MỚI NHẤT (v3) của dự án.

Đọc số liệu thật từ thesis-latex/img/exp/ (đã train v3) và vẽ:
  - Sơ đồ kiến trúc LSTM forecaster (đúng bản hiện tại)
  - Vòng lặp RL (Agent-Environment)  -> cho slide RL đang trống
  - Sơ đồ PPO actor-critic + bảng cấu hình
  - Bảng Input (8 biến) / Output (4 hành động) của PPO
  - Công thức + thành phần Reward (v3, outcome-based)
  - Đường cong train LSTM (loss/accuracy) + ma trận nhầm lẫn (simulator & Kaggle)
  - Đường cong reward PPO
  - Benchmark 4 controller + benchmark theo kịch bản
  - Sơ đồ kiến trúc hệ thống 4 lớp

Chạy:
    python make_slide_figures.py
Tùy chọn:
    python make_slide_figures.py --exp thesis-latex/img/exp --out slide_figures

Yêu cầu: numpy, matplotlib  (KHÔNG cần TensorFlow/SB3 — chạy nhanh, nhẹ).
"""
import os, sys, json, csv, argparse, math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

ROOT = os.path.dirname(os.path.abspath(__file__))
BLUE="#2E75B6"; DARK="#1F4E79"; RED="#C00000"; GREEN="#2E7D32"; ORANGE="#E8A33D"; GREY="#7F7F7F"

def loadj(exp, name, default=None):
    p=os.path.join(exp,name)
    if not os.path.exists(p): print(f"  [bỏ qua] thiếu {name}"); return default
    return json.load(open(p,encoding="utf-8"))

def loadcsv(exp, name):
    p=os.path.join(exp,name)
    if not os.path.exists(p): print(f"  [bỏ qua] thiếu {name}"); return None
    rows=list(csv.DictReader(open(p,encoding="utf-8")))
    return rows

def box(ax,x,y,w,h,text,fc,ec="#333",fs=11,tc="#000",bold=False,round=True):
    style="round,pad=0.02,rounding_size=0.08" if round else "square,pad=0.02"
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=style,fc=fc,ec=ec,lw=1.4))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs,color=tc,
            fontweight="bold" if bold else "normal",wrap=True)

def arrow(ax,x1,y1,x2,y2,color="#333",lw=1.8):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=16,color=color,lw=lw))

# ---------------------------------------------------------------- 1) LSTM arch
def fig_lstm_arch(exp,out):
    fig,ax=plt.subplots(figsize=(11,4.2)); ax.axis("off"); ax.set_xlim(0,11); ax.set_ylim(0,4.2)
    ax.text(5.5,4.0,"Kiến trúc LSTM Forecaster (bản hiện tại)",ha="center",fontsize=14,fontweight="bold",color=DARK)
    # input
    box(ax,0.2,1.4,2.1,1.4,"INPUT\nChuỗi 60 bước x 3 đặc trưng\n(gas, temp, humidity)\nđã chuẩn hoá [0,1]","#CFE2F3",fs=10)
    layers=[("LSTM (32 units)","#9FC5E8"),("Dropout (0.2)","#FFE599"),
            ("Dense (16, ReLU)","#D9A6E8"),("Dense (1, Sigmoid)","#D9A6E8")]
    x=2.7; w=1.7
    prevx=2.3; prevy=2.1
    for i,(t,c) in enumerate(layers):
        box(ax,x,1.5,w,1.2,t,c,fs=10)
        arrow(ax,prevx if i==0 else x-0.4,2.1,x,2.1)
        prevx=x+w; x+=w+0.4
    box(ax,x,1.2,2.0,1.8,"OUTPUT\npredictedRisk5Min\n= P(gas>1000ppm\ntrong 5 phut toi)\n-> riskLabel","#B6D7A8",fs=10,bold=True)
    arrow(ax,prevx,2.1,x,2.1)
    ax.text(5.5,0.7,"Tong tham so ~5.000  |  Bai toan: phan loai nhi phan tren chuoi thoi gian (forecasting)",
            ha="center",fontsize=10,color=GREY,style="italic")
    p=os.path.join(out,"01_lstm_architecture.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)

# ---------------------------------------------------------------- 2) RL loop
def fig_rl_loop(exp,out):
    fig,ax=plt.subplots(figsize=(9,5)); ax.axis("off"); ax.set_xlim(0,9); ax.set_ylim(0,5)
    ax.text(4.5,4.7,"Vong lap tuong tac Agent - Environment (RL)",ha="center",fontsize=14,fontweight="bold",color=DARK)
    box(ax,1.0,2.6,2.6,1.3,"AGENT (PPO)\nBo dieu khien khi gas","#9FC5E8",fs=12,bold=True)
    box(ax,5.4,2.6,2.6,1.3,"ENVIRONMENT\nMo phong vat ly khi gas","#B6D7A8",fs=12,bold=True)
    arrow(ax,3.6,3.55,5.4,3.55,color=BLUE); ax.text(4.5,3.75,"Action a_t\n(NO_OP/ALERT/FAN/VALVE)",ha="center",fontsize=9,color=BLUE)
    arrow(ax,5.4,2.85,3.6,2.85,color=RED)
    ax.text(4.5,1.95,"State s_t (8 chieu) + Reward r_t",ha="center",fontsize=9,color=RED)
    ax.text(4.5,0.8,"Agent chon hanh dong -> moi truong phan hoi trang thai moi + phan thuong ->\nagent cap nhat chinh sach de cuc dai hoa tong reward",
            ha="center",fontsize=10,color=GREY,style="italic")
    p=os.path.join(out,"02_rl_loop.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)

# ---------------------------------------------------------------- 3) PPO actor-critic
def fig_ppo_arch(exp,out):
    fig,ax=plt.subplots(figsize=(10,4.6)); ax.axis("off"); ax.set_xlim(0,10); ax.set_ylim(0,4.6)
    ax.text(5,4.3,"Kien truc PPO Actor-Critic (MlpPolicy)",ha="center",fontsize=14,fontweight="bold",color=DARK)
    box(ax,0.2,1.7,2.2,1.3,"State (8 chieu)\ngas,temp,hum,slope,\np5,fan,valve,t_act","#CFE2F3",fs=9)
    box(ax,2.9,1.7,1.6,1.3,"Dense 64\n(tanh)","#9FC5E8",fs=10)
    box(ax,4.8,1.7,1.6,1.3,"Dense 64\n(tanh)","#9FC5E8",fs=10)
    box(ax,7.0,2.7,2.6,1.1,"Policy head\n4 logits -> softmax","#D9A6E8",fs=10)
    box(ax,7.0,1.0,2.6,1.1,"Value head\nV(s) (scalar)","#FFE599",fs=10)
    arrow(ax,2.4,2.35,2.9,2.35); arrow(ax,4.5,2.35,4.8,2.35)
    arrow(ax,6.4,2.35,7.0,3.25); arrow(ax,6.4,2.35,7.0,1.55)
    ax.text(5,0.4,"Trunk dung chung 2 lop Dense 64 (tanh) -> tach policy head (4 hanh dong) + value head. ~5.000 tham so.",
            ha="center",fontsize=9.5,color=GREY,style="italic")
    p=os.path.join(out,"03_ppo_actor_critic.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)

# ---------------------------------------------------------------- 4) input/output table
def _table(ax,col_labels,rows,colw,title,header_fc=BLUE):
    ax.axis("off")
    n=len(rows)+1; rh=1.0/max(n,1)
    x0=0.02; y=1-rh
    # header
    cx=x0
    for j,c in enumerate(col_labels):
        ax.add_patch(Rectangle((cx,y),colw[j],rh,fc=header_fc,ec="white"))
        ax.text(cx+0.01,y+rh/2,c,va="center",ha="left",fontsize=10,color="white",fontweight="bold")
        cx+=colw[j]
    for i,r in enumerate(rows):
        y-=rh; cx=x0; fc="#F2F7FC" if i%2 else "#FFFFFF"
        for j,c in enumerate(r):
            ax.add_patch(Rectangle((cx,y),colw[j],rh,fc=fc,ec="#DDDDDD"))
            ax.text(cx+0.01,y+rh/2,c,va="center",ha="left",fontsize=9.5,color="#222",
                    fontfamily="monospace" if j==0 else None)
            cx+=colw[j]
    ax.set_title(title,fontsize=12,fontweight="bold",color=DARK)

def fig_ppo_io(exp,out):
    fig,axs=plt.subplots(1,2,figsize=(13,4.4))
    obs=[("gas_norm","Gas hien tai (chuan hoa)"),("temp_norm","Nhiet do (chuan hoa)"),
         ("hum_norm","Do am (chuan hoa)"),("slope_norm","Xu huong tang/giam gas"),
         ("p_critical_5min","Gia tri du doan tu LSTM"),("fan_on","Trang thai quat"),
         ("valve_closed","Trang thai van"),("time_since_action","Thoi gian tu lan dieu khien")]
    _table(axs[0],["Bien (8)","Y nghia"],obs,[0.42,0.58],"INPUT PPO (8 chieu)")
    act=[("0  NO_OP","Khong dieu khien"),("1  ALERT_USER","Canh bao nguoi dung"),
         ("2  FAN_ON","Bat quat thong gio"),("3  CLOSE_VALVE","Dong van gas")]
    _table(axs[1],["Action","Y nghia"],act,[0.42,0.58],"OUTPUT PPO (4 hanh dong)")
    p=os.path.join(out,"04_ppo_input_output.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)

# ---------------------------------------------------------------- 5) reward
def fig_reward(exp,out):
    fig,ax=plt.subplots(figsize=(11,5.2)); ax.axis("off"); ax.set_ylim(0,1); ax.set_xlim(0,1)
    ax.text(0.5,0.95,"Ham Reward (v3 - outcome based)",ha="center",fontsize=14,fontweight="bold",color=DARK)
    formula=(r"$R_t = -0.05 - 50\cdot\mathbb{1}[gas\geq1000] + 0.3\cdot\mathbb{1}[leaking \wedge gas<1000]$"
             "\n"
             r"$\quad -3\cdot\mathbb{1}[ALERT,NORMAL] -15\cdot\mathbb{1}[FAN,NORMAL] -25\cdot\mathbb{1}[VALVE,NORMAL]$"
             "\n"
             r"$\quad -0.5\cdot\mathbb{1}[valve\_closed \wedge NORMAL] -0.1\cdot\mathbb{1}[fan\_on \wedge NORMAL]$")
    ax.text(0.5,0.80,formula,ha="center",va="center",fontsize=12)
    rows=[("-50  (gas >= 1000 ppm)","Phat nang khi de moi truong nguy hiem (bo sot)",RED),
          ("+0.3 (dang ro ri, gas < 1000)","Thuong khi THUC SU kiem soat duoc ro ri",GREEN),
          ("-3 / -15 / -25 (NORMAL)","Phat ALERT/FAN/VALVE sai luc binh thuong",ORANGE),
          ("-0.5 / -0.1 holding cost","Tranh giu van/quat khong can thiet (NORMAL)",ORANGE),
          ("-0.05 moi buoc","Khuyen khich xu ly dut khoat",GREY)]
    y=0.55
    for t,d,c in rows:
        ax.add_patch(Rectangle((0.06,y-0.035),0.30,0.07,fc=c,ec="none",alpha=0.85))
        ax.text(0.21,y,t,ha="center",va="center",fontsize=10,color="white",fontweight="bold")
        ax.text(0.40,y,d,ha="left",va="center",fontsize=10.5,color="#222")
        y-=0.10
    ax.text(0.5,0.03,"Da bo phan thuong +10/buoc cua ban cu (gay reward hacking).",
            ha="center",fontsize=10,color=GREY,style="italic")
    p=os.path.join(out,"05_reward.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)

# ---------------------------------------------------------------- 6) lstm training curve
def fig_lstm_training(exp,out):
    rows=loadcsv(exp,"lstm_history.csv")
    if not rows: return
    ep=[int(r["epoch"]) for r in rows]
    def col(k): return [float(r[k]) for r in rows] if k in rows[0] else None
    fig,ax=plt.subplots(1,2,figsize=(11,4))
    ax[0].plot(ep,col("loss"),label="train",color=BLUE)
    if col("val_loss"): ax[0].plot(ep,col("val_loss"),label="val",color=ORANGE)
    ax[0].set_title("LSTM Loss"); ax[0].set_xlabel("epoch"); ax[0].legend(); ax[0].grid(alpha=.3)
    ax[1].plot(ep,col("accuracy"),label="train",color=BLUE)
    if col("val_accuracy"): ax[1].plot(ep,col("val_accuracy"),label="val",color=ORANGE)
    ax[1].set_title("LSTM Accuracy"); ax[1].set_xlabel("epoch"); ax[1].legend(); ax[1].grid(alpha=.3)
    p=os.path.join(out,"06_lstm_training.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)

# ---------------------------------------------------------------- 7/9) confusion matrices
def _cm(ax,tp,fp,tn,fn,title):
    M=np.array([[tn,fp],[fn,tp]],float); Mr=M/np.maximum(M.sum(1,keepdims=True),1)
    im=ax.imshow(Mr,cmap="Blues",vmin=0,vmax=1)
    ax.set_xticks([0,1]); ax.set_yticks([0,1])
    ax.set_xticklabels(["Pred 0","Pred 1"]); ax.set_yticklabels(["True 0","True 1"])
    for i in range(2):
        for j in range(2):
            ax.text(j,i,f"{int(M[i,j])}\n({Mr[i,j]*100:.1f}%)",ha="center",va="center",
                    color="white" if Mr[i,j]>0.5 else "black",fontsize=11)
    ax.set_title(title,fontsize=12,fontweight="bold")

def fig_cm(exp,out):
    m=loadj(exp,"lstm_metrics.json")
    if m:
        fig,ax=plt.subplots(figsize=(4.8,4.2)); _cm(ax,m["tp"],m["fp"],m["tn"],m["fn"],
            f"LSTM simulator (Acc {m['accuracy']*100:.1f}%)")
        p=os.path.join(out,"07_lstm_confusion_matrix.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)
    k=loadj(exp,"lstm_metrics_kaggle.json")
    if k:
        fig,ax=plt.subplots(figsize=(4.8,4.2)); _cm(ax,k["tp"],k["fp"],k["tn"],k["fn"],
            f"LSTM Kaggle thuc (Acc {k['accuracy']*100:.1f}%)")
        p=os.path.join(out,"09_lstm_confusion_matrix_kaggle.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)

# ---------------------------------------------------------------- 8) kaggle training (copy existing)
def fig_kaggle_copy(exp,out):
    import shutil
    src=os.path.join(exp,"lstm_training_kaggle.png")
    if os.path.exists(src):
        dst=os.path.join(out,"08_lstm_training_kaggle.png"); shutil.copy(src,dst); print("  ok",dst)

# ---------------------------------------------------------------- 10) ppo reward
def fig_ppo_reward(exp,out):
    rows=loadcsv(exp,"ppo_progress.csv")
    if not rows: return
    t=[float(r["cum_t"]) for r in rows]; r=[float(x["r"]) for x in rows]
    ma=[float(x["ma"]) for x in rows] if "ma" in rows[0] else None
    fig,ax=plt.subplots(figsize=(9,4))
    ax.plot(t,r,alpha=0.25,color=BLUE,label="reward / episode")
    if ma: ax.plot(t,ma,color=RED,lw=2,label="moving average")
    ax.set_xlabel("timesteps"); ax.set_ylabel("episode reward"); ax.legend(); ax.grid(alpha=.3)
    ax.set_title("PPO learning curve (v3, outcome-based + VecNormalize)")
    p=os.path.join(out,"10_ppo_reward.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)

# ---------------------------------------------------------------- 11) benchmark
def fig_benchmark(exp,out):
    b=loadj(exp,"benchmark_results.json")
    if not b: return
    ctrls=["threshold","forecaster","rule","rl"]; labels=["THRESHOLD","FORECASTER","RULE","RL"]
    cols=[GREY,BLUE,ORANGE,RED]
    miss=[b[c]["miss_rate"][0]*100 for c in ctrls]; miss_e=[b[c]["miss_rate"][1]*100 for c in ctrls]
    alarm=[b[c]["alarms_per_hour"][0] for c in ctrls]; alarm_e=[b[c]["alarms_per_hour"][1] for c in ctrls]
    peak=[b[c]["mean_peak_gas"][0] for c in ctrls]; peak_e=[b[c]["mean_peak_gas"][1] for c in ctrls]
    fig,ax=plt.subplots(1,3,figsize=(13,4))
    for a,(v,e,t,u) in zip(ax,[(miss,miss_e,"Miss rate (gas cham 1000ppm)","%"),
                               (alarm,alarm_e,"Canh bao sai","alarm/gio"),
                               (peak,peak_e,"Peak gas trung binh","ppm")]):
        a.bar(labels,v,yerr=e,color=cols,capsize=4)
        a.set_title(t); a.set_ylabel(u); a.tick_params(axis="x",rotation=20)
        for i,val in enumerate(v): a.text(i,val,f"{val:.0f}" if val>10 else f"{val:.1f}",ha="center",va="bottom",fontsize=9)
    fig.suptitle("Benchmark 4 bo dieu khien (3 seed x 4h) - RL vuot troi moi chi so",fontweight="bold")
    p=os.path.join(out,"11_benchmark_chart.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)

# ---------------------------------------------------------------- 12) scenarios
def fig_scenarios(exp,out):
    s=loadj(exp,"scenarios_results.json")
    if not s: return
    ctrls=["threshold","forecaster","rule","rl"]; labels=["THRESHOLD","FORECASTER","RULE","RL"]
    cols=[GREY,BLUE,ORANGE,RED]; scen=["slow","fast"]
    fig,ax=plt.subplots(1,2,figsize=(12,4.4)); x=np.arange(len(ctrls))
    for j,sc in enumerate(scen):
        peak=[s[f"{sc}/{c}"]["peak"] for c in ctrls]; lead=[s[f"{sc}/{c}"]["lead_s"] for c in ctrls]
        crit=[s[f"{sc}/{c}"]["reached_critical_rate"] for c in ctrls]
        a=ax[j]; a.bar(x,peak,0.6,color=cols); a.axhline(1000,ls="--",color="red",lw=1,label="CRITICAL 1000ppm")
        a.set_title(f"Kich ban {sc.upper()}: peak gas + lead time"); a.set_xticks(x); a.set_xticklabels(labels,rotation=20)
        a.set_ylabel("peak gas (ppm)")
        for i,(pv,lv,cr) in enumerate(zip(peak,lead,crit)):
            a.text(i,pv,f"peak {pv:.0f}\nlead {lv:.0f}s\n{'CRIT' if cr>0 else 'OK'}",ha="center",va="bottom",fontsize=7.5)
        a.legend(fontsize=8)
    p=os.path.join(out,"12_scenarios_chart.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)

# ---------------------------------------------------------------- 13) system architecture
def fig_system(exp,out):
    fig,ax=plt.subplots(figsize=(12,5)); ax.axis("off"); ax.set_xlim(0,12); ax.set_ylim(0,5)
    ax.text(6,4.7,"Kien truc he thong IoT 4 lop",ha="center",fontsize=14,fontweight="bold",color=DARK)
    layers=[("LOP THIET BI","ESP32 / Sensor Simulator\n(MQ gas, DHT22)","#CFE2F3"),
            ("LOP TRUYEN THONG","Mosquitto MQTT\n-> MQTT-Kafka bridge -> Kafka","#9FC5E8"),
            ("LOP XU LY","Spark Streaming\nLSTM forecaster + PPO controller","#B6D7A8"),
            ("LOP UNG DUNG","Backend API, Dashboard,\nGrafana, Telegram bot","#FFE599")]
    x=0.3; w=2.7
    for i,(t,d,c) in enumerate(layers):
        box(ax,x,1.5,w,2.0,t+"\n\n"+d,c,fs=10,bold=False)
        ax.text(x+w/2,3.25,t,ha="center",fontsize=10.5,fontweight="bold",color=DARK)
        if i<3: arrow(ax,x+w,2.5,x+w+0.3,2.5,color=BLUE)
        x+=w+0.3
    ax.text(6,0.7,"InfluxDB (time-series) + PostgreSQL (alert/action) | Docker Compose",
            ha="center",fontsize=10,color=GREY,style="italic")
    p=os.path.join(out,"13_system_architecture.png"); plt.tight_layout(); plt.savefig(p,dpi=150); plt.close(); print("  ok",p)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--exp",default=os.path.join(ROOT,"thesis-latex","img","exp"))
    ap.add_argument("--out",default=os.path.join(ROOT,"slide_figures"))
    a=ap.parse_args()
    os.makedirs(a.out,exist_ok=True)
    print(f"Doc artifacts tu: {a.exp}")
    print(f"Xuat hinh ra:     {a.out}\n")
    figs=[fig_lstm_arch,fig_rl_loop,fig_ppo_arch,fig_ppo_io,fig_reward,
          fig_lstm_training,fig_cm,fig_kaggle_copy,fig_ppo_reward,
          fig_benchmark,fig_scenarios,fig_system]
    for f in figs:
        try: f(a.exp,a.out)
        except Exception as e: print(f"  [LOI] {f.__name__}: {e}")
    print("\nXong. Mo thu muc slide_figures/ de lay hinh dan vao slide.")

if __name__=="__main__":
    main()

from django.views.generic import TemplateView
import plotly.graph_objects as go
from django.shortcuts import render
import pandas as pd

from chart_studio.plotly import plot as py
import plotly.graph_objs as go
import numpy as np
import math


class BacklingAllowance():
    def __init__(self,area, ability,torsionalconstant, lb, E, G, F, Iw=None, M1=None, M2=None, doublecurve=False):
        self.area = area #断面積
        self.ability = ability #断面二次モーメントと断面係数のリスト [断面二次モーメント強, 弱, 断面係数強, 弱]
        self.torsionalconstant = torsionalconstant #サンブナンねじり定数
        self.lb = lb #座屈長
        self.E = E #ヤング係数
        self.G = G #横弾性係数
        self.F = F #基準強度
        if Iw == None:  #曲げねじり定数
            self.Iw = 0
        else:
            self.Iw = Iw
        
        if M1 and M2 and M1 < M2:
            self.M1 = M2 #M1のほうが大きい
            self.M2 = M1 #M2が小さいほう
        else:   
            self.M1 = M1
            self.M2 = M2 
        self.doublecurve = doublecurve #複曲率
        
    def SR(self): #細長比
        I_W = self.ability[1]
        i = (I_W/self.area)**0.5
        sr = self.lb/i
        return sr
    
    def LSR(self): #限界細長比
        lsr = math.pi*(self.E/0.6/self.F)**0.5
        return lsr
    
    def BacklingCompression(self): #圧縮座屈
        v = 1.5+2/3*((self.SR()/self.LSR())**2)
        
        if self.SR() <= self.LSR():
            fc = 1/v*(1-0.4*(self.SR()/self.LSR())**2)*self.F
        else:
            fc= 0.277*((self.LSR()/self.SR())**2)*self.F
        return fc
    
    def BacklingBend(self): #曲げ座屈
        I_W = self.ability[1] #弱軸の断面二次モーメント
        Z_W = self.ability[3] #弱軸の断面係数
        
        if self.M1 and self.M2: #支点間距離端部に最大曲げモーメントが発生する場合
            if self.doublecurve:
                M_ratio = -(self.M2/self.M1)
            else:
                M_ratio = self.M2/self.M1
            C = 1.75+1.05*M_ratio+0.3*M_ratio**2
            if C>=2.3:
                C = 2.3
            PLB = 0.6+0.3*M_ratio
        else:  #支点間距離内部に最大曲げモーメントが発生する場合
            C = 1.0    
            PLB = 0.3
        ELB = 1.29
        
        My = self.F*Z_W #降伏モーメント
        Me = C*(((math.pi**4)*(self.E**2)*I_W*self.Iw)/(self.lb**4) + (math.pi**2)*self.E*I_W*self.G*self.torsionalconstant/(self.lb)**2)**0.5 #弾性横座屈モーメント
        LambdaB = (My/Me)**0.5
        v = 1.5+2/3*(LambdaB/ELB)**2
        
        if LambdaB < PLB:
            fb = self.F/v
        elif PLB< LambdaB <= ELB:
            fb = (((1-0.4*(LambdaB-PLB)/(ELB-PLB))*self.F)/v)
        elif ELB < LambdaB:
            fb = 1/LambdaB**2*self.F/2.17
        
        return fb
    
    def main(self):
        return self.BacklingCompression(),self.BacklingBend()

class Rectangle_Ability():
    def __init__(self, height,width,lb, E, G, F, M1=None, M2=None,doublecurve = False):
        if height>width:
            self.L = height
            self.S = width
        else:
            self.L = width
            self.S = height

        self.lb = lb
        self.E = E #ヤング係数
        self.G = G #横弾性係数
        self.F = F #基準強度
        
        self.M1=M1
        self.M2=M2
        self.doublecurve = doublecurve
        
    def Area(self):
        area = self.L*self.S
        return area
    
    def ability(self):
        I_S = self.S*self.L**3/12 #SecondMoment_断面二次モーメント 
        I_W = self.S**3*self.L/12
        Z_S = I_S/(self.L/2)    #ElasticModulus＿断面係数
        Z_W = I_W/(self.S/2)
        return I_S, I_W, Z_S,Z_W
    
    def TorsionalConstant(self):
        Ix = self.L*self.S**3/16*(16/3-3.36*self.S/self.L*(1-1/12*(self.S/self.L)**4))

        return Ix
    
    def main(self):
        area = self.Area()
        ability = list(self.ability())
        torsionalconstant = self.TorsionalConstant()
        ba = BacklingAllowance(area, ability, torsionalconstant, self.lb, self.E, self.G, self.F, self.M1, self.M2, self.doublecurve)
        return ba.main()




def index(request):
    
    x = np.linspace(1, 100, 100)
    y = np.linspace(1, 100, 100)

    xx, yy = np.meshgrid(x, y) # 格子点となるx,y座標を作成。

    p_list = []
    b_list = []

    for i in x:
        for j in y:
            r = Rectangle_Ability(i, j, 5000, 205000, 79000, 235) 
            p,b = r.main()
            p_list.append(p)
            b_list.append(b)
    p_list = np.reshape(p_list,(100,100))
    b_list = np.reshape(b_list,(100,100))

    def plot_wireframe(xx, yy, z, color='#0066FF', linewidth=1):
        """ワイヤーフレームをプロットする"""
        line_marker = dict(color=color, width=linewidth)
        lines = []
        for i, j, k in zip(xx, yy, z):
            lines.append(go.Scatter3d(x=i, y=j, z=k, mode='lines', line=line_marker))
            lines.append(go.Scatter3d(x=j, y=i, z=k, mode='lines', line=line_marker))
            #lines.append(go.Scatter3d(x=j, y=i, z=-k, mode='lines', line=line_marker))
            
        layout = go.Layout(showlegend=False)
        return go.Figure(data=lines, layout=layout)

    fig1 = plot_wireframe(xx, yy, p_list)
    fig1.update_layout(margin=dict(l=10, r=10, b=10, t=10),width=1200,height=900,)
    fig1.update_layout(title=dict(text='<b>長期許容圧縮応力度',
                                font=dict(size=26,
                                        color='grey'),
                                y=0.88))

    plot_fig1 = fig1.to_html(fig1, include_plotlyjs=False)
    
    
    
    fig2 = plot_wireframe(xx, yy, b_list)
    fig2.update_layout(margin=dict(l=10, r=10, b=10, t=10),width=1200,height=900,)
    fig2.update_layout(title=dict(text='<b>長期許容曲げ応力度',
                                font=dict(size=26,
                                        color='grey'),
                                y=0.88))

    plot_fig2 = fig2.to_html(fig2, include_plotlyjs=False)
    return render(request, "plot/plot.html", {"graph1": plot_fig1,
                                            "graph2": plot_fig2})
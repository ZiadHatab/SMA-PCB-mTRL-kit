"""
Ziad (https://github.com/ZiadHatab)
"""
import os  

# need to be installed via pip: python -m pip install scikit-rf numpy matplotlib -U
import skrf as rf
import numpy as np
import matplotlib.pyplot as plt

# my script (MultiCal.py and TUGmTRL must also be in same folder)
from mTRL import mTRL

class PlotSettings:
    # to make plots look better for publication
    # https://matplotlib.org/stable/tutorials/introductory/customizing.html
    def __init__(self, font_size=10, latex=False): 
        self.font_size = font_size 
        self.latex = latex
    def __enter__(self):
        plt.style.use('seaborn-v0_8-paper')
        # make svg output text and not curves
        plt.rcParams['svg.fonttype'] = 'none'
        # fontsize of the axes title
        plt.rc('axes', titlesize=self.font_size*1.2)
        # fontsize of the x and y labels
        plt.rc('axes', labelsize=self.font_size)
        # fontsize of the tick labels
        plt.rc('xtick', labelsize=self.font_size)
        plt.rc('ytick', labelsize=self.font_size)
        # legend fontsize
        plt.rc('legend', fontsize=self.font_size*1)
        # fontsize of the figure title
        plt.rc('figure', titlesize=self.font_size)
        # controls default text sizes
        plt.rc('text', usetex=self.latex)
        #plt.rc('font', size=self.font_size, family='serif', serif='Times New Roman')
        plt.rc('lines', linewidth=1.5)
    def __exit__(self, exception_type, exception_value, traceback):
        plt.style.use('default')

def plot_2x2(NW, fig, axs, f_units='ghz', name='mTRL', title='mTRL'):
    NW.frequency.unit = f_units
    NW.name = name
    for inx in NW.port_tuples:
        m = inx[0]
        n = inx[1]
        NW.plot_s_db(m=m, n=n, ax=axs[inx])
    fig.suptitle(title)
    fig.tight_layout(pad=1.08)


def get_switch(S):
    Gf = []
    Gr = []
    f = S[0].frequency.f
    for inx in range(len(f)):
        H = np.array([[ -s.s[inx,0,0]*s.s[inx,0,1]/s.s[inx,1,0], -s.s[inx,1,1], 1, s.s[inx,0,1]/s.s[inx,1,0]  ]  for s in S])
        _,_,vh = np.linalg.svd(H)
        nullspace = vh[-1,:].conj()
        Gf.append(nullspace[1]/nullspace[2])
        Gr.append(nullspace[0]/nullspace[3])
    
    return np.array(Gf), np.array(Gr)


# main script
if __name__ == '__main__':
    # useful functions
    c0 = 299792458   # speed of light in vacuum (m/s)
    mag2db = lambda x: 20*np.log10(abs(x))
    db2mag = lambda x: 10**(x/20)
    gamma2ereff = lambda x,f: -(c0/2/np.pi/f*x)**2
    ereff2gamma = lambda x,f: 2*np.pi*f/c0*np.sqrt(-(x-1j*np.finfo(complex).eps))  # eps to ensure positive square-root
    gamma2dbcm  = lambda x: mag2db(np.exp(x.real*1e-2))  # losses dB/cm
    path = os.path.dirname(os.path.realpath(__file__)) + '\\'
    
    # load the measurements
    # files' path are reference to script's path
    s2p_path = os.path.dirname(os.path.realpath(__file__)) + '\\Measurements\\'
    
    fmax = 20
    fmin = 0.1
    
    # switch terms
    Gamma_21 = rf.Network(s2p_path + 'Gamma_21.s1p')[f'{fmin}ghz-{fmax}ghz']
    Gamma_12 = rf.Network(s2p_path + 'Gamma_12.s1p')[f'{fmin}ghz-{fmax}ghz']
    
    # Calibration standards
    L1    = rf.Network(s2p_path + 'line_0_0mm.s2p')[f'{fmin}ghz-{fmax}ghz']
    L2    = rf.Network(s2p_path + 'line_2_5mm.s2p')[f'{fmin}ghz-{fmax}ghz']
    L3    = rf.Network(s2p_path + 'line_10_0mm.s2p')[f'{fmin}ghz-{fmax}ghz']
    L4    = rf.Network(s2p_path + 'line_15_0mm.s2p')[f'{fmin}ghz-{fmax}ghz']
    L5    = rf.Network(s2p_path + 'line_50_0mm.s2p')[f'{fmin}ghz-{fmax}ghz']
    SHORT = rf.Network(s2p_path + 'short_0_0mm.s2p')[f'{fmin}ghz-{fmax}ghz']
    
    DUT = rf.Network(s2p_path + 'step_line.s2p')[f'{fmin}ghz-{fmax}ghz']
    
    f = L1.frequency.f
    
    ## the calibration    
    lines = [L1, L2, L3, L4, L5]
    line_lengths = [0e-3, 2.5e-3, 10e-3, 15e-3, 50e-3]
    reflect = [SHORT]
    reflect_est = [-1]
    reflect_offset = [0]
        
    cal = mTRL(lines=lines, line_lengths=line_lengths, reflect=reflect, 
               reflect_est=reflect_est, reflect_offset=reflect_offset, ereff_est=3.5+0j,
               switch_term=[Gamma_21, Gamma_12]
               )
    
    cal.run_multical()
    ereff_nist = cal.ereff
    gamma_nist = cal.gamma
    dut_cal_nist = cal.apply_cal(DUT)
    
    cal.run_tug()
    ereff_tug = cal.ereff
    gamma_tug = cal.gamma
    dut_cal_tug = cal.apply_cal(DUT)
    
    
    with PlotSettings(14):
        fig, axs = plt.subplots(2,2, figsize=(10,7))        
        fig.set_dpi(600)
        fig.tight_layout(pad=3)
        ax = axs[0,0]
        val = mag2db(dut_cal_nist.s[:,0,0])
        ax.plot(f*1e-9, val, lw=2.5, marker='o', markevery=30, markersize=12,
                label='NIST mTRL', linestyle='-')
        val = mag2db(dut_cal_tug.s[:,0,0])
        ax.plot(f*1e-9, val, lw=2.5, marker='X', markevery=30, markersize=10,
                label='TUG mTRL', linestyle='-')
        ax.set_xlabel('Frequency (GHz)')
        ax.set_xticks(np.arange(0,20.1,2))
        ax.set_xlim(0,20)
        ax.set_ylabel('S11 (dB)')
        ax.set_yticks(np.arange(-40,0.1,10))
        ax.set_ylim(-40,0)
        ax.axvspan(14, 16, color='orange', alpha=0.3)
        ax.axvspan(16, 20, color='red', alpha=0.3)
        
        ax = axs[0,1]
        val = mag2db(dut_cal_nist.s[:,1,0])
        ax.plot(f*1e-9, val, lw=2.5, marker='o', markevery=30, markersize=12,
                label='NIST mTRL', linestyle='-')
        val = mag2db(dut_cal_tug.s[:,1,0])
        ax.plot(f*1e-9, val, lw=2.5, marker='X', markevery=30, markersize=10,
                label='TUG mTRL', linestyle='-')
        ax.set_xlabel('Frequency (GHz)')
        ax.set_xticks(np.arange(0,20.1,2))
        ax.set_xlim(0,20)
        ax.set_ylabel('S21 (dB)')
        ax.set_yticks(np.arange(-4,0.1,1))
        ax.set_ylim(-4,0)
        ax.legend(loc='lower left', ncol=1, fontsize=12)
        ax.axvspan(14, 16, color='orange', alpha=0.3)
        ax.axvspan(16, 20, color='red', alpha=0.3)
        
        ax = axs[1,0]
        val = np.angle(dut_cal_nist.s[:,0,0], deg=True)
        ax.plot(f*1e-9, val, lw=2.5, marker='o', markevery=30, markersize=12,
                label='NIST mTRL', linestyle='-')
        val = np.angle(dut_cal_tug.s[:,0,0], deg=True)
        ax.plot(f*1e-9, val, lw=2.5, marker='X', markevery=30, markersize=10,
                label='TUG mTRL', linestyle='-')
        ax.set_xlabel('Frequency (GHz)')
        ax.set_xticks(np.arange(0,20.1,2))
        ax.set_xlim(0,20)
        ax.set_ylabel('S11 (deg)')
        ax.set_ylim(-180,180)
        ax.set_yticks(np.arange(-180,181,60))
        ax.axvspan(14, 16, color='orange', alpha=0.3)
        ax.axvspan(16, 20, color='red', alpha=0.3)
        
        ax = axs[1,1]
        val = np.angle(dut_cal_nist.s[:,1,0], deg=True)
        ax.plot(f*1e-9, val, lw=2.5, marker='o', markevery=30, markersize=12,
                label='NIST mTRL', linestyle='-')
        val = np.angle(dut_cal_tug.s[:,1,0], deg=True)
        ax.plot(f*1e-9, val, lw=2.5, marker='X', markevery=30, markersize=10,
                label='TUG mTRL', linestyle='-')
        ax.set_xlabel('Frequency (GHz)')
        ax.set_xticks(np.arange(0,20.1,2))
        ax.set_xlim(0,20)
        ax.set_ylabel('S21 (deg)')
        ax.set_ylim(-180,180)
        ax.set_yticks(np.arange(-180,181,60))
        ax.axvspan(14, 16, color='orange', alpha=0.3)
        ax.axvspan(16, 20, color='red', alpha=0.3)
        
    with PlotSettings(14):
        fig, axs = plt.subplots(1,2, figsize=(10,3.8))        
        fig.set_dpi(600)
        fig.tight_layout(pad=2)
        ax = axs[0]
        ax.plot(f*1e-9, ereff_nist.real, lw=2, label='NIST mTRL', 
                marker='o', markevery=30, markersize=12)
        ax.plot(f*1e-9, ereff_tug.real, lw=2, label='TUG mTRL', 
                marker='X', markevery=30, markersize=10)
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('Relative dielectric constant')
        ax.set_yticks(np.arange(3.5, 4.51, 0.2))
        ax.set_ylim([3.5, 4.5])
        ax.set_xticks(np.arange(0,20.1,2))
        ax.set_xlim(0,20)
        ax.axvspan(14, 16, color='orange', alpha=0.3)
        ax.axvspan(16, 20, color='red', alpha=0.3)
        ax.legend()
        
        ax = axs[1]
        ax.plot(f*1e-9, gamma2dbcm(gamma_nist), lw=2, label='NIST mTRL', 
                marker='o', markevery=30, markersize=10)
        ax.plot(f*1e-9, gamma2dbcm(gamma_tug), lw=2, label='TUG mTRL', 
                marker='X', markevery=30, markersize=10)
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('Loss (dB/cm)')
        ax.set_ylim([0, 1])
        ax.set_yticks(np.arange(0, 1.1, 0.2))
        ax.set_xticks(np.arange(0,20.1,2))
        ax.set_xlim(0,20)
        ax.axvspan(14, 16, color='orange', alpha=0.3)
        ax.axvspan(16, 20, color='red', alpha=0.3)
        
    plt.show()
    
# EOF
import sys
import cv2
import os
import imutils
path_above = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '../..'))
dirpath = path_above+'/Joystick/Images/HUD'
sys.path.append(path_above)
from collections import deque
import numpy as np
from TBotTools import tbt, pid, geometry, pgt
import bluetooth as bt
import pygame
from sys import exit
import pygame.gfxdraw
pygame.init()
textPrint = pgt.TextPrint((255,255,255))
textPrint.setlineheight(25)
background = pygame.image.load(dirpath+'/BGTracker.png')
connecting = pygame.image.load(dirpath+'/offline.png')
scalefactor = 1
origin =  [130,20] # Cam image origin
geom = geometry.geometry(1) # scale factor to convert pixels to mm
arrow = np.array([[2,0],[2,50],[7,50],[0,65],[-7,50],[-2,50],[-2,0],[2,0]])
bb = np.array([[0,0,],[0,1],[1,1],[2,0],[3,0],[4,0],[3,0],[2,0],[1,0]])

#----------------------------------------------------------------------#
#                        Configure Camera
#----------------------------------------------------------------------#
camwidth = 640
camheight = 360
camorigin = origin
cam = cv2.VideoCapture(0,cv2.CAP_V4L2)
cam.set(cv2.CAP_PROP_AUTOFOCUS, 0)
cam.set(28, 0)
cam.set(cv2.CAP_PROP_GAIN,0)
cam.set(cv2.CAP_PROP_BRIGHTNESS,0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
cam.set(cv2.CAP_PROP_BRIGHTNESS, 100)
sidebarwidth = 1
maskgridL = np.meshgrid(np.r_[0:360],np.r_[0:sidebarwidth])
maskgridR = np.meshgrid(np.r_[0:360],np.r_[640-sidebarwidth:640])

#----------------- empty lists for disk positions  --------------------#
x = []
y = []
x2 = []
y2 = []
x3 = []
y3 = []
tolerance = 20
angle = 0 # inital target angle
distance = 0 # initial target distance
#----------------------------------------------------------------------#
#                           Setup plotting
#----------------------------------------------------------------------#
xdatarange = [618,834]
iii = xdatarange[1]-xdatarange[0]
y_origin = 438
yscale = 100
plot_pts = deque(maxlen=xdatarange[1]-xdatarange[0])
plot_pts2 = deque(maxlen=xdatarange[1]-xdatarange[0])
plot_pts3 = deque(maxlen=xdatarange[1]-xdatarange[0])

for ii in range(xdatarange[0],xdatarange[1]):
    plot_pts.appendleft((ii,0))
    plot_pts2.appendleft((ii,0))
    plot_pts3.appendleft((ii,0))

plot_aa = np.zeros((len(plot_pts),2))
plot_aa[:,1]=np.array(plot_pts)[:,1]
plot_aa[:,0]=np.array(range(xdatarange[0],xdatarange[1]))
plot_cc = np.zeros((len(plot_pts),2))
plot_cc[:,1]=np.array(plot_pts2)[:,1]
plot_cc[:,0]=np.array(range(xdatarange[0],xdatarange[1]))
plot_bb=np.copy(plot_aa)
plot_dd=np.copy(plot_cc)

#----------------------------------------------------------------------#
#                        Set HSV Thresholds
#            Use getHSVThresh.py to find the correct values
#----------------------------------------------------------------------#

greenLower = (41,76,0)  # place green disc on the left.
greenUpper = (93,255,255) 
 
redLower = (145,81,27)       
redUpper = (255,255,255) # place red disc on the right

blueLower = (98,234,126)       
blueUpper = (158,255,255) # Blue fin on helmet

#------------- Initialise Bluetooth data variables --------------------#
data = [0,0,0,0]
sendcount = 0

#----------------------------------------------------------------------#
#                    For Linux / Raspberry Pi
#----------------------------------------------------------------------#
#    use: 'hcitool scan' to scan for your T-Bot address
#    Note: you will have to connect to the T-Bot using your 
#    system's bluetooth application using the 1234 as the password
#----------------------------------------------------------------------#

bd_addr = '98:D3:51:FD:82:95' # George
#bd_addr = '98:D3:71:FD:46:9C' # Trailblazer

port = 1
btcom = tbt.bt_connect(bd_addr,port,'PyBluez') # PyBluez works well for the Raspberry Pi
#btcom = tbt.bt_connect(bd_addr,port,'Socket')

#----------------------------------------------------------------------#
#                       For Windows and Mac
#----------------------------------------------------------------------#
#port = 'COM5'
#port = '/dev/tty.George-DevB'
#baudrate = 38400
#bd_addr = 'Empty'
#btcom = tbt.bt_connect(bd_addr,port,'PySerial',baudrate)

#----------------------------------------------------------------------#
#                         Start main loop 
#----------------------------------------------------------------------#


done = 0
screen = pygame.display.set_mode((900, 590))

#-----------------------------------------------------------------------
#                         Tracking PID setup
#-----------------------------------------------------------------------
rotspeed = 200 # range is 100 to 300 with 200 being zero
dt = 0.005
feedforward = 2
pkp_o = 2.02
pki_o = 0.4
pkd_o = 0
akp_o = 0.68
aki_o = 0.4
akd_o = 0.01
FW_o = 2
FW = FW_o
FW_old = FW_o
pkp_old = pkp_o
pki_old = pki_o
pkd_old = pkd_o
akp_old = akp_o
aki_old = aki_o
akd_old = akd_o
pos_pid = pid.pid(pkp_o,pki_o,pkd_o,[-10,10],[0,20],dt)
angle_pid = pid.pid(akp_o,aki_o,akd_o,[-15,15],[-60,60],dt)

#----------------------------------------------------------------------#
#                         Create slider bars
#----------------------------------------------------------------------#
barcolour = (150,150,150)
spotcolour = (255,10,0)
sbar = pgt.SliderBar(screen, (100,450-30), pkp_o, 460, 5, 4, barcolour,spotcolour)
sbar2 = pgt.SliderBar(screen, (100,475-30), pki_o, 460, 5, 4, barcolour,spotcolour)
sbar3 = pgt.SliderBar(screen, (100,500-30), pkd_o, 460, 0.5, 4, barcolour,spotcolour)

sbar4 = pgt.SliderBar(screen, (100,525-30), akp_o, 460, 5, 4, barcolour,spotcolour)
sbar5 = pgt.SliderBar(screen, (100,550-30), aki_o, 460, 5, 4, barcolour,spotcolour)
sbar6 = pgt.SliderBar(screen, (100,575-30), akd_o, 460, 0.5, 4, barcolour,spotcolour)
sbar7 = pgt.SliderBar(screen, (100,600-30), FW, 460, 100, 4, barcolour,spotcolour)

#----------------------------------------------------------------------#
#                       Set window name 
#----------------------------------------------------------------------#
pygame.display.set_caption("Track and Chase")

#----------------------------------------------------------------------#
#                      Start main loop
#----------------------------------------------------------------------#
if __name__ == '__main__':
    #-------------------------------------------------------------------
    #                   Track T-Bot  
    #-------------------------------------------------------------------
    while cam.isOpened():
        success, frame = cam.read()
        if not success:
            print('Problems Connecting to Camera')
            break
        frame[maskgridL] = 0
        frame[maskgridR] = 0       
        screen.blit(background,(0,0))
        #---------------------------------------------------------------
        #                 Listen for user events
        #---------------------------------------------------------------
        events = pygame.event.get()
        keys = pygame.key.get_pressed()
        c1, c2, c3 =  pygame.mouse.get_pressed()
        mx,my = pygame.mouse.get_pos()
        #---------------------------------------------------------------
        #                     Draw Slide Bars
        #---------------------------------------------------------------
        pkp = sbar.get_mouse_and_set()
        pki = sbar2.get_mouse_and_set()
        pkd = sbar3.get_mouse_and_set()
        akp = sbar4.get_mouse_and_set()
        aki = sbar5.get_mouse_and_set()
        akd = sbar6.get_mouse_and_set()
        FW = sbar7.get_mouse_and_set()
        #---------------------------------------------------------------
        #               Update tuning from slider bars
        #---------------------------------------------------------------
        if pkp != pkp_old:
            pos_pid.set_PID(pkp,pki,pkd)
            pkp_old = pkp
            
        if pki != pki_old:
            pos_pid.set_PID(pkp,pki,pkd)
            pki_old = pki

        if pkd != pkd_old:
            pos_pid.set_PID(pkp,pki,pkd)
            pkd_old = pkd
            
        if akp != akp_old:
            angle_pid.set_PID(akp,aki,akd)
            akp_old = akp

        if aki != aki_old:
            angle_pid.set_PID(akp,aki,akd)
            aki_old = aki

        if akd != akd_old:
            angle_pid.set_PID(akp,aki,akd)
            akd_old = akd

        if FW_old != feedforward:
            angle_pid.set_PID(akp,aki,akd)
            feedforward = FW
        #---------------------------------------------------------------
        #            Check Status of Bluetooth Connection
        #---------------------------------------------------------------
        if ~btcom.connected():
            tries = 0
            while btcom.connected() < 1 and tries < 10:
                screen.blit(connecting,(0,0))
                pygame.display.flip()
                print('Connecting ...')              
                try:
                    print('Try '+str(tries+1)+' of 10')
                    btcom.connect(0)
                    btcom.connect(1)
                    tries+=1
                except:
                    print('Something went wrong')                  
            if btcom.connected() < 1:
                print('Exiting Program')
                sys.exit()
            else:
                tries = 0
                data = btcom.get_data(data)
                
        #---------------------------------------------------------------
        #        Track red and green discs and oponents blue fin 
        #---------------------------------------------------------------

        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV) # do this outside function so it is not done twice
        try:         
            x, y, center, radius, M, cents = geom.tracker(hsv, greenLower, greenUpper)
            if radius > 1:
                cv2.circle(frame, (int(x), int(y)), int(radius),(0, 255, 0), 2)
                cv2.circle(frame, center, 2, (0, 255, 0), -1)
        except:
            pass
        try:
            x2, y2, center2, radius2, M2, cents2 = geom.tracker(hsv, redLower, redUpper)
            if radius2 > 1:
                cv2.circle(frame, (int(x2), int(y2)), int(radius2),(113,212,198), 2)
                cv2.circle(frame, center2, 2, (113,212,198), -1)
        except:
            pass
        try:
            x3, y3, center3, radius3, M3, cents3 = geom.tracker(hsv, blueLower, blueUpper)
            if radius3 > 1:
                cv2.circle(frame, (int(x3), int(y3)), int(radius3),(113,212,198), 2)
                cv2.circle(frame, center3, 2, (113,212,198), -1)
        except:
            pass

        #---------------------------------------------------------------
        #               Battle and control strategy
        #---------------------------------------------------------------
        
        if x != [] and x2 !=[] and x3!=[]:
            distance = geom.distance((x,y),(x2,y2),(x3,y3)) # distance to target coordinate
            if np.abs(distance) < tolerance:
                abc = 'You could add some extra logic here for battle AI'
                #angle = geom.angle((x,y),(x2,y2),(x3,y3))+90 # Turn the T-Bot so spikes point to opponent
            else:
                angle = geom.angle((x,y),(x2,y2),(x3,y3))

            rotspeed = 200+angle_pid.output(0,-angle)
            forwardspeed = 200+(pos_pid.output(0,-distance)+FW)
            #-----------------------------------------------------------
            #          build data string to send to T-Bot
            #-----------------------------------------------------------
            rotspeed = '%03d' % rotspeed
            forwardspeed = '%03d' % forwardspeed
            #-----------------------------------------------------------
            #                  Send Data To T-Bot
            #-----------------------------------------------------------
            sendstr = str(rotspeed)+str(forwardspeed)+'Z'
            sendcount = btcom.send_data(sendstr,sendcount)
            
        #---------------------------------------------------------------
        #          Basic Trim Controls for The T-Bot
        #---------------------------------------------------------------
        if keys[pygame.K_t]:
            buttonstring = '200200T' # Auto trim
            sendcount = btcom.send_data(buttonstring,sendcount)
        if keys[pygame.K_n]:
            buttonstring = '200200E' # -ve trim
            sendcount = btcom.send_data(buttonstring,sendcount)
        if keys[pygame.K_p]:
            buttonstring = '200200F' # +ve trim
            sendcount = btcom.send_data(buttonstring,sendcount)

        #---------------------------------------------------------------
        #            Reset tuning to default settings 
        #---------------------------------------------------------------

        if keys[pygame.K_r]:       
            pos_pid.set_PID(pkp_o,pki_o,pkd_o)
            angle_pid.set_PID(akp_o,aki_o,akd_o)
            sbar.set_pos2(pkp_o)
            sbar2.set_pos2(pki_o)
            sbar3.set_pos2(pkd_o)
            sbar4.set_pos2(akp_o)
            sbar5.set_pos2(aki_o)
            sbar6.set_pos2(akd_o)
            sbar7.set_pos2(FW_o)
            pos_pid.clear()
            angle_pid.clear()
        if keys[pygame.K_q]: # Quit and exit
            cam.release()
            sendcount = btcom.send_data('200200Z',sendcount)
            btcom.connect(0)
            break
            
        #---------------------------------------------------------------
        #            Add data points for plotting 
        #---------------------------------------------------------------          
        plot_pts.appendleft((iii,angle))
        plot_pts2.appendleft((iii,distance))
        iii+=1
        if iii > xdatarange[1]:
            iii = xdatarange[0]
        plot_aa[:,1]=np.array(plot_pts)[:,1]
        plot_cc[:,1]=np.array(plot_pts2)[:,1]
        pygame.draw.lines(screen, (0,255,255), False, ((xdatarange[0],y_origin+0.5*yscale),(xdatarange[1],y_origin+0.5*yscale)),1)
        try:  
            plot_bb[:,1] = (yscale/((plot_aa[:,1]-plot_aa[:,1].max()).min())*(plot_aa[:,1]-plot_aa[:,1].max()))+y_origin
            plot_dd[:,1] = (yscale/((plot_cc[:,1]-plot_cc[:,1].max()).min())*(plot_cc[:,1]-plot_cc[:,1].max()))+y_origin
            gdata = tuple(map(tuple, tuple(plot_bb)))
            vdata = tuple(map(tuple, tuple(plot_dd)))
            pygame.draw.lines(screen, (255,255,255,255), False, (gdata),1)
            pygame.draw.lines(screen, (255,0,0,255), False, (vdata),1)
        except Exception:
            pass

        pygame.draw.lines(screen, (0,255,255), False, ((xdatarange[0],y_origin),(xdatarange[0],y_origin+yscale)),1)
        pygame.draw.lines(screen, (0,255,255), False, ((xdatarange[-1],y_origin),(xdatarange[-1],y_origin+yscale)),1)
        textPrint.abspos(screen, "{:+.2f}".format(plot_aa[:,1].max()),[xdatarange[0],y_origin-20])
        textPrint.abspos(screen, "{:+.2f}".format(plot_aa[:,1].min()),[xdatarange[0],y_origin+yscale+5])
        textPrint.tprint(screen,'Angle')
        textPrint.setColour((255,0,0,255))
        textPrint.abspos(screen, "{:+.2f}".format(plot_cc[:,1].max()),[xdatarange[-1],y_origin-20])
        textPrint.abspos(screen, "{:+.2f}".format(plot_cc[:,1].min()),[xdatarange[-1],y_origin+yscale+5])
        textPrint.tprint(screen,'Distance')
        textPrint.setColour((255,255,255,255))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = pygame.image.frombuffer(frame.tostring(),frame.shape[1::-1],'RGB')
        screen.blit(frame,camorigin)
        textPrint.abspos(screen, "pkp: {:.3f}".format(pkp),(10,416))
        textPrint.tprint(screen, "pki: {:.3f}".format(pki))
        textPrint.tprint(screen, "pkd: {:.3f}".format(pkd))
        textPrint.tprint(screen, "akp: {:.3f}".format(akp))
        textPrint.tprint(screen, "aki: {:.3f}".format(aki))
        textPrint.tprint(screen, "akd: {:.3f}".format(akd))
        textPrint.tprint(screen, "FW: {:.3f}".format(FW))
        try:
            orient = geom.orientation(center2,center)
        except:
            orient = geom.orientation([0,0],[1,1])
        arrow_rot1 = np.array(geom.rotxy(orient[1]*np.pi/180,arrow))
        arrow1_tup = tuple(map(tuple, tuple((arrow_rot1+orient[0]+origin).astype(int))))
        pygame.gfxdraw.filled_polygon(screen, (arrow1_tup), (0,255,255,155))
        pygame.gfxdraw.aapolygon(screen, (arrow1_tup), (0,255,255,200))
        arrow_rot2 = np.array(geom.rotxy((angle+orient[1])*np.pi/180,arrow))
        arrow2_tup = tuple(map(tuple, tuple((arrow_rot2+orient[0]+origin).astype(int))))
        pygame.gfxdraw.filled_polygon(screen, (arrow2_tup), (255,255,255,155))
        pygame.gfxdraw.aapolygon(screen, (arrow2_tup), (0,255,255,200))
        pygame.display.flip()

cv2.destroyAllWindows()
pygame.display.quit()



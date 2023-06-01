from machine import Pin,I2C
from neopixel import NeoPixel
from MX1508 import *
from VL53L0X import *
from tcs34725 import *
from time import sleep_ms,sleep
import uasyncio as asio
#import aioespnow
import network

i2c_bus = I2C(0, sda=Pin(21), scl=Pin(22))
tcs = TCS34725(i2c_bus)
tcs.gain(4)#gain must be 1, 4, 16 or 60
tcs.integration_time(80)
i2c_bus1 = I2C(1, sda=Pin(19), scl=Pin(18))
tof = VL53L0X(i2c_bus1)
NUM_OF_LED = 2
np = NeoPixel(Pin(13), NUM_OF_LED)
color=['Red','Yellow','White','Green','Black','Cyan','Blue','Magenta']
dir_move=['Stop','Forward','Left','Right','Reverse']
motor_L = MX1508(33, 32)
motor_R = MX1508(25, 26)
Sp=1023
Lt=60
alfa=0.8
debug=1

R_W_count,W_count,col_id,col_id_l,direct,di,dist,busy,busy_col=0,0,0,0,0,0,500,0,0
L_count=0
delta = [0] *2
d_count=0
col_sel_r=4
col_sel=["Black"]
R_m_pin = Pin(27, Pin.IN)
L_m_pin = Pin(14, Pin.IN)

motor_R.forward(1023)
motor_L.forward(1023)

#"""
#C8F09E4E9CA8
#E05A1B757D04

# A WLAN interface must be active to send()/recv()
#network.WLAN(network.STA_IF).active(True)
#e.active(True)
#peer = b'\xC8\xF0\x9E\x52\x66\x0C' #C8F09E52660C
#'\\x'+mac[0:2]+'\\x'+mac[2:4]+'\\x'+mac[4:6]+'\\x'+mac[6:8]+'\\x'+mac[8:10]+'\\x'+mac[10:12]
#e.add_peer(peer)
#peer = b'\xC8\xF0\x9E\x4E\x9C\xA8' #C8F09E4E9CA8
#e.add_peer(peer)
#peer = b'\xCC\xDB\xA7\x56\x9C\x0C' #CCDBA7569C0C
#e.add_peer(peer)
#"""

def R_W_int(pin):
    global W_count,R_W_count
    W_count+=1
    R_W_count+=1
    
def L_W_int(pin):
    global L_count
    L_count+=1
   
R_m_pin.irq(trigger=Pin.IRQ_FALLING |Pin.IRQ_RISING , handler=R_W_int) #t    rigger=Pin.IRQ_FALLING | 
L_m_pin.irq(trigger=Pin.IRQ_FALLING |Pin.IRQ_RISING , handler=L_W_int)

async def synch(int_ms):
    global W_count,L_count, direct,d_count
    Sp1=int(Sp*0.6)
    print(Sp1)
    U_count = 10
    while 1:
        await asio.sleep_ms(int_ms)
        await spin(1)
        if direct==0:
            if d_count>U_count:
                motor_R.forward(Sp1)
                motor_L.forward(Sp)
            elif d_count<-U_count:
                motor_R.forward(Sp)
                motor_L.forward(Sp1)
            else:
                motor_R.forward(Sp)
                motor_L.forward(Sp)
        if direct==1:
            if d_count>U_count:
                motor_R.forward(Sp1)
                motor_L.reverse(Sp)
            elif d_count<-U_count:
                motor_R.forward(Sp)
                motor_L.reverse(Sp1)
            else:
                motor_R.forward(Sp)
                motor_L.reverse(Sp)
        elif direct==2:
            if d_count>U_count:
                motor_R.reverse(Sp1)
                motor_L.forward(Sp)
            elif d_count<-U_count:
                motor_R.reverse(Sp)
                motor_L.forward(Sp1)
            else:
                motor_R.reverse(Sp)
                motor_L.forward(Sp)        
        elif direct==3:
            if d_count>U_count:
                motor_R.reverse(Sp1)
                motor_L.reverse(Sp)
            elif d_count<-U_count:
                motor_R.reverse(Sp)
                motor_L.reverse(Sp1)
            else:
                motor_R.reverse(Sp)
                motor_L.reverse(Sp)
        elif direct==-1:
            motor_R.reverse(0)
            motor_L.reverse(0)

async def spin(int_ms):
    global W_count,L_count, direct,delta 
    await asio.sleep_ms(int_ms*100)
    delta[1]=W_count-L_count
    d_count=delta[1]-delta[0]
    delta[0]=delta[1]
    #print(direct,d_count)
        
async def W_sp(int_ms):
    global di,direct,busy_col
    while 1:
        await asio.sleep_ms(int_ms)
        await color_det()
        await dist_det()
        if 150<dist<250:di=1
        elif dist<150:di=2
        else:di=0
        if (not busy) & (not busy_col):
            if di==1:
                if dist%2:
                    direct=1
                else:
                    direct=2
                await move(8)
            elif di==2:
                direct=3
                await move(16)
            else:
                direct=0
        if  col_id==4:
            direct=3
            await move(8)
            direct=2
            await move(16)
        if  color[col_id] in col_sel:
            direct=-1
            busy_col=1
        else:
            motor_R.reverse(Sp)
            motor_L.forward(Sp)
            busy_col=0
        if color[col_sel_r] in col_sel:
            col_sel.remove(color[col_sel_r])
if debug:
    print(col_sel)
                      
async def move(turn):
    global R_W_count,busy
    busy=1
    R_W_count=0    
    while R_W_count<turn:   
        await asio.sleep_ms(0)
    busy=0

async def color_det():
    global col_id,col_id_l
    rgb=tcs.read(1)
    r,g,b=rgb[0],rgb[1],rgb[2]
    h,s,v=rgb_to_hsv(r,g,b)
    if 0<h<60:
        col_id_l=col_id
        col_id=0
    elif 61<h<120:
        col_id_l=col_id
        col_id=1
    elif 121<h<180:
        if v>100:
            col_id_l=col_id
            col_id=2
        elif 25<v<100:
            col_id_l=col_id
            col_id=3
        elif v<25:
            col_id_l=col_id
            col_id=4
    elif 181<h<240:
        if v>40:
            col_id_l=col_id
            col_id=5
        else:
            col_id_l=col_id
            col_id=6
    elif 241<h<360:
        col_id_l=col_id
        col_id=7 
    if debug:
        print('Color is {}. R:{} G:{} B:{} H:{:.0f} S:{:.0f} V:{:.0f}'.format(color[col_id],r,g,b,h,s,v))      
            
async def dist_det():
    global dist
    tof.start()
    dist_l=dist
    dist=tof.read()-65
    tof.stop()
    dist=int(alfa*dist+(1-alfa)*dist_l)
    if debug:
        print('Distance is {}. W_count {}'.format(dist   ,W_count))
        
async def LED_cont(int_ms):
    while 1:
        await asio.sleep_ms(int_ms)
        if col_id==0:
            np[0]=(Lt,0,0)
        elif col_id==1:
            np[0]=(Lt,Lt,0)
        elif col_id==2:
            np[0]=(Lt,Lt,Lt)
        elif col_id==3:
            np[0]=(0,Lt,0)
        elif col_id==4:
            np[0]=(0,0,0)
            np.write()
            await asio.sleep_ms(300)
            np[0]=(Lt,0,0)
            np.write()
            await asio.sleep_ms(300)
        elif col_id==5:
            np[0]=(0,Lt,Lt)
        elif col_id==6:
            np[0]=(0,0,Lt) 
        elif col_id==7:
            np[0]=(Lt,0,Lt)
        if di==0:
            np[1]=(0,Lt,0)
        elif di==1:
            np[1]=(Lt,Lt,0)
        elif di==2:
            np[1]=(Lt,0,0)
        np.write()
        
#async def send(e, period):
    #while 1:
        #await asio.sleep_ms(period)
        #if busy_col:
            #await e.asend(str(col_id))
            
        
#async def resive(e,int_ms):
    #global col_sel_r
    #while 1:
        #async for mac, msg in e:
            #col_sel_r=int.from_bytes(msg,'big')-48
            #await asio.sleep_ms(int_ms)
            
# define loop
loop = asio.get_event_loop()

#create looped tasks
loop.create_task(W_sp(100))
loop.create_task(synch(5))
loop.create_task(LED_cont(100))
#loop.create_task(send(e, 100))
# loop run forever
loop.run_forever()
import serial
import struct
import time

'''
Author  : Yahboom Team
Version : V1.1.5
LastEdit: 2025.07.09
'''


"""
ORDER 用来存放命令地址和对应数据
ORDER is used to store the command address and corresponding data
"""
ORDER = {
    "MOTOR_PID": [0x13, 0, 0, 0, 0, 0, 0, 0],
    "IMU_YAW_PID": [0x14, 0, 0, 0, 0, 0, 0, 0],

    "CAR_TYPE": [0x15, 0],

    "ARM_TORQUE": [0x22, 0],
    "ARM_OFFSET": [0x24, 0, 0],
    "ARM_MID_VALUE": [0x25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],

    "DOMAIN_ID": [0x41, 0, 0],
    "ROS_NAMESPACE": [0x42, 0, 0],
    "ROS_SCALE_LINE": [0x43, 0, 0, 0],
    "ROS_SCALE_ANGULAR": [0x44, 0, 0, 0],

    "ROBOT_REBOOT": [0x80, 0, 0],
    "ROBOT_CONFIG": [0x81, 0, 0],

    "REQUEST_DATA": [0x50, 0, 0],
    "FIRMWARE_VERSION": [0x51],
}


class MicroROS_Robot():

    def __init__(self, port="/dev/myserial", debug=False):
        self.__ser = serial.Serial(port, 2000000, timeout=0.05)
        self.__rx_FLAG = 0
        self.__rx_COUNT = 0
        self.__rx_ADDR = 0
        self.__rx_LEN = 0
        self.__RX_BUF_LEN_MAX = 40
        self.__rx_DATA = bytearray(self.__RX_BUF_LEN_MAX)
        self.__send_delay = 0.01
        self.__read_delay = 0.01
        self.__debug = debug
        self.__data_changed = False

        self.__HEAD = 0xFF
        self.__DEVICE_ID = 0xFC
        self.__RETURN_ID = self.__DEVICE_ID - 1
        self.__COMPLEMENT = 257 - self.__DEVICE_ID
        self.__READ_DATA = 0x50


        self.CAR_TYPE = 7
        


    # 发送一些数据到设备 Send some data to device
    def __send(self, key, len=1):
        self.__data_changed = True
        order = ORDER[key][0]
        value = []
        value_sum = self.__COMPLEMENT
        for i in range(0, len):
            value.append(ORDER[key][1 + i])
            value_sum = value_sum + ORDER[key][1 + i]
        sum_data = (self.__HEAD + self.__DEVICE_ID + (len + 0x03) + order + value_sum) % 256
        tx = [self.__HEAD, self.__DEVICE_ID, (len + 0x03), order]
        tx.extend(value)
        tx.append(sum_data)
        self.__ser.write(tx)
        if self.__send_delay > 0:
            time.sleep(self.__send_delay)
        if self.__debug:
            print ("Send: [0x" + ', 0x'.join('{:02X}'.format(x) for x in tx) + "]")
            # print ("Send: [" + ' '.join('{:02X}'.format(x) for x in tx) + "]")

    # 发送请求数据 Send request data
    def __request(self, addr, param=0):
        order = self.__READ_DATA
        buf_len = 5
        sum_data = (buf_len + order + addr + param) % 256
        tx = [self.__HEAD, self.__DEVICE_ID, buf_len, order, addr, param, sum_data]
        self.__ser.flushInput()
        self.__ser.flushOutput()
        for i in range(self.__RX_BUF_LEN_MAX):
            self.__rx_DATA[i] = 0
        self.__ser.write(tx)
        if self.__debug:
            print ("Read: [0x" + ', 0x'.join('{:02X}'.format(x) for x in tx) + "]")
            # print ("Read: [" + ' '.join('{:02X}'.format(x) for x in tx) + "]")

    # 解析数据 parse data
    def __unpack(self):
        n = self.__ser.inWaiting()
        rx_CHECK = 0
        if n <= 0:
            return False
        #print("OK")
        data_array = self.__ser.read_all()
        if self.__debug:
            # print("rx_data:", list(data_array))
            print ("rx_data: [0x" + ', 0x'.join('{:02X}'.format(x) for x in data_array) + "]")
            # print ("rx_data: [" + ' '.join('{:02X}'.format(x) for x in data_array) + "]")
        for data in data_array:
            if self.__rx_FLAG == 0:
                if data == self.__HEAD:
                    self.__rx_FLAG = 1
                else:
                    self.__rx_FLAG = 0

            elif self.__rx_FLAG == 1:
                if data == self.__RETURN_ID:
                    self.__rx_FLAG = 2
                else:
                    self.__rx_FLAG = 0

            elif self.__rx_FLAG == 2:
                self.__rx_LEN = data
                self.__rx_FLAG = 3

            elif self.__rx_FLAG == 3:
                self.__rx_ADDR = data
                self.__rx_FLAG = 4
                self.__rx_COUNT = 0

            elif self.__rx_FLAG == 4:
                if self.__rx_COUNT < self.__rx_LEN - 3:
                    self.__rx_DATA[self.__rx_COUNT] = data
                    self.__rx_COUNT = self.__rx_COUNT + 1
                if self.__rx_COUNT >= (self.__rx_LEN - 3):
                    self.__rx_FLAG = 5


            elif self.__rx_FLAG == 5:
                for value in self.__rx_DATA:
                    rx_CHECK = rx_CHECK + value
                rx_CHECK = (self.__rx_LEN + self.__rx_ADDR + rx_CHECK) % 256
                if data == rx_CHECK:
                    self.__rx_FLAG = 0
                    self.__rx_COUNT = 0
                    return True
                else:
                    if self.__debug:
                        print("check error:", rx_CHECK, data)
                    self.__rx_FLAG = 0
                    self.__rx_COUNT = 0
                    self.__rx_ADDR = 0
                    self.__rx_LEN = 0
        return False


    # 重启设备 reboot device
    def reboot_device(self):
        ORDER["ROBOT_REBOOT"][1] = 0x5F
        ORDER["ROBOT_REBOOT"][2] = 0x5F
        self.__send("ROBOT_REBOOT", len=2)
        time.sleep(2)
        # self.__ser.setDTR(False)
        # self.__ser.setRTS(True)
        # time.sleep(.1)
        # self.__ser.setDTR(True)
        # self.__ser.setRTS(True)
        # time.sleep(2)
    
    # 恢复出厂配置, 重启生效
    # Restore factory Settings, Restart to take effect
    def reset_factory_config(self):
        ORDER["ROBOT_CONFIG"][1] = 0
        ORDER["ROBOT_CONFIG"][2] = 0x5F
        self.__send("ROBOT_CONFIG", len=2)
        time.sleep(2)

    # 更新配置数据到机器人上
    def update_config_data(self):
        if self.__data_changed:
            ORDER["ROBOT_CONFIG"][1] = 1
            ORDER["ROBOT_CONFIG"][2] = 0x5F
            self.__send("ROBOT_CONFIG", len=2)
            self.__data_changed = False
            time.sleep(2)



    def set_arm_mid_value(self, mid_value=[2000, 2000, 2000, 2000, 1486, 3100]):
        if 1600 <= mid_value[0] <= 2400 and 1600 <= mid_value[1] <= 2400 and 1600 <= mid_value[2] <= 2400 and \
            1600 <= mid_value[3] <= 2400 and 1186 <= mid_value[4] <= 1786 and 2700 <= mid_value[5] <= 3500:
            value_s1 = bytearray(struct.pack('h', int(mid_value[0])))
            value_s2 = bytearray(struct.pack('h', int(mid_value[1])))
            value_s3 = bytearray(struct.pack('h', int(mid_value[2])))
            value_s4 = bytearray(struct.pack('h', int(mid_value[3])))
            value_s5 = bytearray(struct.pack('h', int(mid_value[4])))
            value_s6 = bytearray(struct.pack('h', int(mid_value[5])))

            ORDER["ARM_MID_VALUE"][1] = value_s1[0]
            ORDER["ARM_MID_VALUE"][2] = value_s1[1]
            ORDER["ARM_MID_VALUE"][3] = value_s2[0]
            ORDER["ARM_MID_VALUE"][4] = value_s2[1]
            ORDER["ARM_MID_VALUE"][5] = value_s3[0]
            ORDER["ARM_MID_VALUE"][6] = value_s3[1]
            ORDER["ARM_MID_VALUE"][7] = value_s4[0]
            ORDER["ARM_MID_VALUE"][8] = value_s4[1]
            ORDER["ARM_MID_VALUE"][9] = value_s5[0]
            ORDER["ARM_MID_VALUE"][10] = value_s5[1]
            ORDER["ARM_MID_VALUE"][11] = value_s6[0]
            ORDER["ARM_MID_VALUE"][12] = value_s6[1]
            ORDER["ARM_MID_VALUE"][13] = 0
            self.__send("ARM_MID_VALUE", len=13)
        else:
            print("mid_value input error!")

    def set_arm_torque(self, enable):
        '''
        设置机械臂扭力开关，enable=1表示打开扭力，enable=0表示关闭扭力。
        '''
        if enable > 0:
            on = 1
        else:
            on = 0
        ORDER["ARM_TORQUE"][1] = on
        temp = self.__data_changed
        self.__send("ARM_TORQUE", len=1)
        self.__data_changed = temp
    
    def set_arm_calib_offset(self, arm_id):
        '''
        机械臂校准功能。
        输入参数示例:arm_id=1。arm_id取值范围: 1 <= domain_id <= 6, 表示校准对应舵机的中值。
        '''
        if arm_id < 1 or arm_id > 6:
            return
        ORDER["ARM_OFFSET"][1] = int(arm_id) & 0xFF
        ORDER["ARM_OFFSET"][2] = 0
        for i in range(self.__RX_BUF_LEN_MAX):
            self.__rx_DATA[i] = 0
        self.__ser.flushInput()
        temp = self.__data_changed
        self.__send("ARM_OFFSET", len=2)
        self.__data_changed = temp
        state = -1
        for k in range(6):
            time.sleep(.5)
            if self.__unpack():
                if self.__rx_DATA[0] == arm_id:
                    state = self.__rx_DATA[1]
                    return state
        return state

    def set_arm_calib_offset_all(self):
        '''
        校准机械臂所有舵机功能。
        '''
        for i in range(6):
            state = robot.set_arm_calib_offset(i+1)
            print("state:", i+1, state)
            time.sleep(.5)

    # Configure the ROS DOMAIN ID. Restart takes effect.
    def set_ros_domain_id(self, domain_id):
        '''
        配置ROS DOMAIN ID。重启生效。
        输入参数示例:domain_id=30。domain_id取值范围: 0 <= domain_id <= 100
        '''
        if domain_id < 0 or domain_id > 101:
            return
        ORDER["DOMAIN_ID"][1] = int(domain_id) & 0xFF
        ORDER["DOMAIN_ID"][2] = 0
        self.__send("DOMAIN_ID", len=2)


    # Configure the ROS namespace. Restart to take effect
    def set_ros_namespace(self, ros_namespace):
        """
        配置ROS命名空间。重启生效
        输入参数示例: ros_namespace="robot1"
        """
        name_len = len(ros_namespace)
        if name_len > 10 or name_len < 0:
            return
        name_buf = [0 for i in range(10)]
        name_bytes = bytes(str(ros_namespace), "utf-8")
        for i in range(10):
            if i < len(ros_namespace):
                name_buf[i] = name_bytes[i]
        ORDER["ROS_NAMESPACE"].extend(name_buf)
        ORDER["ROS_NAMESPACE"][1] = name_len
        ORDER["ROS_NAMESPACE"][2] = 0
        self.__send("ROS_NAMESPACE", len=12)

    # Configure the ROS scale_line. Restart to take effect
    def set_ros_scale_line(self, scale=1.0):
        """
        配置ROS线速度缩放比例。重启生效
        输入参数示例: scale=1.0
        """
        if scale > 2 or scale < 0:
            return
        bytearray_scale = bytearray(struct.pack('h', int(scale*1000)))
        ORDER["ROS_SCALE_LINE"][1] = bytearray_scale[0]
        ORDER["ROS_SCALE_LINE"][2] = bytearray_scale[1]
        ORDER["ROS_SCALE_LINE"][3] = 0
        self.__send("ROS_SCALE_LINE", len=3)

    # Configure the ROS scale_angular. Restart to take effect
    def set_ros_scale_angular(self, scale=1.0):
        """
        配置ROS角速度缩放比例。重启生效
        输入参数示例: scale=1.0
        """
        if scale > 2 or scale < 0:
            return
        bytearray_scale = bytearray(struct.pack('h', int(scale*1000)))
        ORDER["ROS_SCALE_ANGULAR"][1] = bytearray_scale[0]
        ORDER["ROS_SCALE_ANGULAR"][2] = bytearray_scale[1]
        ORDER["ROS_SCALE_ANGULAR"][3] = 0
        self.__send("ROS_SCALE_ANGULAR", len=3)

    # Set motor PID parameters.
    def set_motor_pid_parm(self, pid_p, pid_i, pid_d):
        '''
        设置电机PID参数。
        pid参数取值范围: [0.00, 10.00]
        '''
        pid_p_s = bytearray(struct.pack('h', int(pid_p*100)))
        pid_i_s = bytearray(struct.pack('h', int(pid_i*100)))
        pid_d_s = bytearray(struct.pack('h', int(pid_d*100)))
        ORDER["MOTOR_PID"][1] = pid_p_s[0]
        ORDER["MOTOR_PID"][2] = pid_p_s[1]
        ORDER["MOTOR_PID"][3] = pid_i_s[0]
        ORDER["MOTOR_PID"][4] = pid_i_s[1]
        ORDER["MOTOR_PID"][5] = pid_d_s[0]
        ORDER["MOTOR_PID"][6] = pid_d_s[1]
        ORDER["MOTOR_PID"][7] = 0
        self.__send("MOTOR_PID", len=7)

    # Set IMU YAW PID parameters.
    def set_imu_yaw_pid_parm(self, pid_p, pid_i, pid_d):
        '''
        设置IMU YAW PID参数。
        pid参数取值范围: [0.00, 10.00]
        '''
        pid_p_s = bytearray(struct.pack('h', int(pid_p*100)))
        pid_i_s = bytearray(struct.pack('h', int(pid_i*100)))
        pid_d_s = bytearray(struct.pack('h', int(pid_d*100)))
        ORDER["IMU_YAW_PID"][1] = pid_p_s[0]
        ORDER["IMU_YAW_PID"][2] = pid_p_s[1]
        ORDER["IMU_YAW_PID"][3] = pid_i_s[0]
        ORDER["IMU_YAW_PID"][4] = pid_i_s[1]
        ORDER["IMU_YAW_PID"][5] = pid_d_s[0]
        ORDER["IMU_YAW_PID"][6] = pid_d_s[1]
        ORDER["IMU_YAW_PID"][7] = 0
        self.__send("IMU_YAW_PID", len=7)
    

    def read_car_type(self):
        '''
        读取底板小车类型。
        '''
        self.__request(ORDER["CAR_TYPE"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            car_type = struct.unpack('h', bytearray(self.__rx_DATA[0:2]))[0]
            str_data = str(car_type)
        return str_data

    def read_arm_mid_value(self):
        '''
        读取机械臂校准后的中位值。
        '''
        self.__request(ORDER["ARM_MID_VALUE"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            value_s1 = struct.unpack('h', bytearray(self.__rx_DATA[0:2]))[0]
            value_s2 = struct.unpack('h', bytearray(self.__rx_DATA[2:4]))[0]
            value_s3 = struct.unpack('h', bytearray(self.__rx_DATA[4:6]))[0]
            value_s4 = struct.unpack('h', bytearray(self.__rx_DATA[6:8]))[0]
            value_s5 = struct.unpack('h', bytearray(self.__rx_DATA[8:10]))[0]
            value_s6 = struct.unpack('h', bytearray(self.__rx_DATA[10:12]))[0]
            str_data = "%d,%d,%d,%d,%d,%d" % (value_s1, value_s2, value_s3, value_s4, value_s5, value_s6)
        return str_data



    def read_ros_domain_id(self):
        '''
        读取底板ROS DOMAIN ID
        '''
        self.__request(ORDER["DOMAIN_ID"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            domain_id = self.__rx_DATA[0]
            str_data = "%d" % (domain_id)
        return str_data

    def read_ros_namespace(self):
        '''
        读取底板的ROS命名空间
        '''
        self.__request(ORDER["ROS_NAMESPACE"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            str_data = self.__rx_DATA[1:].decode('utf-8')
        return str_data

    def read_ros_scale_line(self):
        '''
        读取ROS线速度缩放比例系数参数
        '''
        self.__request(ORDER["ROS_SCALE_LINE"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            scale = struct.unpack('h', bytearray(self.__rx_DATA[0:2]))[0]/1000.0
            str_data = "%.3f" % scale
        return str_data
    
    def read_ros_scale_angular(self):
        '''
        读取ROS角速度缩放比例系数参数
        '''
        self.__request(ORDER["ROS_SCALE_ANGULAR"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            scale = struct.unpack('h', bytearray(self.__rx_DATA[0:2]))[0]/1000.0
            str_data = "%.3f" % scale
        return str_data

    def read_motor_pid_parm(self):
        '''
        读取底板电机PID参数
        '''
        self.__request(ORDER["MOTOR_PID"][0], 1)
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            pid_p = struct.unpack('h', bytearray(self.__rx_DATA[1:3]))[0]/1000.0
            pid_i = struct.unpack('h', bytearray(self.__rx_DATA[3:5]))[0]/1000.0
            pid_d = struct.unpack('h', bytearray(self.__rx_DATA[5:7]))[0]/1000.0
            str_data = "%.3f, %.3f, %.3f" % (pid_p, pid_i, pid_d)
        return str_data

    def read_imu_yaw_pid_parm(self):
        '''
        读取底板IMU YAW PID参数
        '''
        self.__request(ORDER["IMU_YAW_PID"][0], 5)
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            pid_p = struct.unpack('h', bytearray(self.__rx_DATA[1:3]))[0]/1000.0
            pid_i = struct.unpack('h', bytearray(self.__rx_DATA[3:5]))[0]/1000.0
            pid_d = struct.unpack('h', bytearray(self.__rx_DATA[5:7]))[0]/1000.0
            str_data = "%.3f, %.3f, %.3f" % (pid_p, pid_i, pid_d)
        return str_data


    def read_version(self):
        '''
        返回固件版本
        Return the firmware version
        '''
        self.__request(ORDER["FIRMWARE_VERSION"][0])
        time.sleep(self.__read_delay)
        str_version = None
        if self.__unpack():
            str_version = "%d.%d.%d" % (self.__rx_DATA[0], self.__rx_DATA[1], self.__rx_DATA[2])
        return str_version

    # 读取并打印所有配置信息。
    # Read and print all configuration information.
    def print_all_firmware_parm(self):
        version = self.read_version()
        print("version:", version)

        domain_id = self.read_ros_domain_id()
        print("domain_id:", domain_id)

        ros_namespace = self.read_ros_namespace()
        print("ros_namespace:", ros_namespace)

        ros_scale_line = self.read_ros_scale_line()
        print("ros_scale_line:", ros_scale_line)

        ros_scale_angular = self.read_ros_scale_angular()
        print("ros_scale_angular:", ros_scale_angular)

 
        motor_pid_parm = self.read_motor_pid_parm()
        print("motor pid parm:", motor_pid_parm)

        imu_pid_parm = self.read_imu_yaw_pid_parm()
        print("imu pid parm:", imu_pid_parm)

        arm_mid = self.read_arm_mid_value()
        print("arm_mid:", arm_mid)






if __name__ == '__main__':

    import platform
    debug = False
    device = platform.system()
    print("Read device:", device)
    if device == 'Windows':
        com_index = 1
        while True:
            com_index = com_index + 1
            try:
                # print("try COM%d" % com_index)
                com = 'COM%d' % com_index
                robot = MicroROS_Robot(com, debug=debug)
                break
            except:
                if com_index > 256:
                    print("-----------------------No COM Open--------------------------")
                    exit(0)
                continue
        print("--------------------Open %s---------------------" % com)
    else:
        robot = MicroROS_Robot(port="/dev/myserial", debug=debug)
    
    print("Waiting to read the car type")
    while True:
        car_type = robot.read_car_type()
        if car_type is not None:
            print("car_type:", car_type)
            if int(car_type) == robot.CAR_TYPE:
                break
        time.sleep(.5)

    
    # robot.set_ros_domain_id(30)
    # robot.set_ros_namespace("")
    # robot.set_motor_pid_parm(0.8, 0.06, 0.5)
    # robot.set_imu_yaw_pid_parm(0.6, 0, 0.3)

    # robot.set_ros_scale_line(1.0)
    # robot.set_ros_scale_angular(1.0)

    # arm_mid_value = [2000, 2000, 2000, 2000, 1486, 3100]
    # robot.set_arm_mid_value(arm_mid_value)
    

    # Please remove the comments. If you need to save the configuration.
    robot.update_config_data()

    # Please remove the comments. If you need to reset configuration.
    # robot.reset_factory_config()


    time.sleep(1)
    robot.print_all_firmware_parm()

    # Please reboot the device to take effect, if you change some device config.
    time.sleep(1)
    robot.reboot_device()

    try:
        while False:
            # robot.beep(100)
            time.sleep(1)
    except:
        pass
    time.sleep(.1)
    del robot

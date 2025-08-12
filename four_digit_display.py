#!/usr/bin/env python
# encoding: utf-8

from gpiozero import LED, Button
import time

class FourDigit7SegmentDisplay:
    """4位7段数码管控制器类"""

    def __init__(self):
        # 定义段LED对应的GPIO口（共阴极，低电平点亮）
        self.segments = {
            'a': LED(26, active_high=False),
            'b': LED(19, active_high=False),
            'c': LED(13, active_high=False),
            'd': LED(6, active_high=False),
            'e': LED(5, active_high=False),
            'f': LED(11, active_high=False),
            'g': LED(9, active_high=False),
            'dp': LED(10, active_high=False)
        }

        # 定义4位数码管对应的GPIO口（位选）
        self.digits = [
            LED(12),  # 第1位
            LED(16),  # 第2位
            LED(20),  # 第3位
            LED(21)   # 第4位
        ]

        # 数字段码映射 (0-9)，对应a,b,c,d,e,f,g的状态
        self.digit_codes = {
            0: [1,1,1,1,1,1,0],
            1: [0,1,1,0,0,0,0],
            2: [1,1,0,1,1,0,1],
            3: [1,1,1,1,0,0,1],
            4: [0,1,1,0,0,1,1],
            5: [1,0,1,1,0,1,1],
            6: [1,0,1,1,1,1,1],
            7: [1,1,1,0,0,0,0],
            8: [1,1,1,1,1,1,1],
            9: [1,1,1,1,0,1,1]
        }

        # 初始化所有LED为关闭状态
        self.clear()

    def clear(self):
        """清除所有显示"""
        # 关闭所有段
        for segment in self.segments.values():
            segment.off()
        # 关闭所有位
        for digit in self.digits:
            digit.off()

    def set_digit(self, digit_pos, number, show_dp=False):
        """
        在指定位置显示数字
        digit_pos: 位置 (0-3 对应第1-4位)
        number: 要显示的数字 (0-9)
        show_dp: 是否显示小数点
        """
        # 验证输入
        if not 0 <= digit_pos < 4:
            return
        if number not in self.digit_codes:
            return

        # 关闭所有位，防止串扰
        for d in self.digits:
            d.off()

        # 设置段码
        code = self.digit_codes[number]
        segment_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
        for i, segment_name in enumerate(segment_list):
            if code[i]:
                self.segments[segment_name].on()
            else:
                self.segments[segment_name].off()

        # 控制小数点
        if show_dp:
            self.segments['dp'].on()
        else:
            self.segments['dp'].off()

        # 打开指定的位
        self.digits[digit_pos].on()

# 创建数码管实例
display = FourDigit7SegmentDisplay()

# 定义按钮（上拉电阻）
button = Button(27, pull_up=True)

try:
    refresh_interval = 0.005  # 刷新间隔，控制数码管闪烁
    while True:
        current_time = time.localtime()

        # 按钮未按下显示时间(HH:MM)，按下显示日期(MM:DD)
        if not button.is_pressed:
            # 显示小时
            hour = current_time.tm_hour
            display.set_digit(0, hour // 10, False)
            time.sleep(refresh_interval)
            display.set_digit(1, hour % 10, True)  # 显示小数点作为分隔符
            time.sleep(refresh_interval)

            # 显示分钟
            minute = current_time.tm_min
            display.set_digit(2, minute // 10, False)
            time.sleep(refresh_interval)
            display.set_digit(3, minute % 10, False)
            time.sleep(refresh_interval)
        else:
            # 显示月份
            month = current_time.tm_mon
            display.set_digit(0, month // 10, False)
            time.sleep(refresh_interval)
            display.set_digit(1, month % 10, True)  # 显示小数点作为分隔符
            time.sleep(refresh_interval)

            # 显示日期
            day = current_time.tm_mday
            display.set_digit(2, day // 10, False)
            time.sleep(refresh_interval)
            display.set_digit(3, day % 10, False)
            time.sleep(refresh_interval)

except KeyboardInterrupt:
    print("程序已停止")
finally:
    display.clear()  # 清除显示
import tkinter as tk
from tkinter import ttk, filedialog
import threading
import serial
from serial.tools import list_ports
import json
import time

class MotorControlApp:
    def __init__(self, master):
        self.master = master
        master.title('Motor Control system tool v1.0 developed by © 孙佩东 2024')
        # 管理程序执行的线程列表
        self.program_threads = []
        self.thread = None  # 初始化线程属性

        # 创建界面切换选择栏
        self.mode_var = tk.StringVar()
        self.mode_var.set("motor_control")
        self.mode_selector = ttk.Combobox(master, textvariable=self.mode_var, values=["motor_control", "preset_program", "program_editing"])
        self.mode_selector.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        self.mode_selector.bind("<<ComboboxSelected>>", self.switch_mode)

        self.motor_control_frame = ttk.Frame(master)
        self.motor_control_frame.grid(row=1, column=0, columnspan=2)
        self.create_motor_control_ui(self.motor_control_frame)

        self.preset_program_frame = ttk.Frame(master)
        self.preset_program_frame.grid(row=1, column=0, columnspan=2)
        self.create_preset_program_ui(self.preset_program_frame)
        self.preset_program_frame.grid_remove()

        self.program_editing_frame = ttk.Frame(master)
        self.program_editing_frame.grid(row=1, column=0, columnspan=2)
        self.create_program_editing_ui(self.program_editing_frame)
        self.program_editing_frame.grid_remove()

        # 设置关闭事件处理器
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_motor_control_ui(self, frame):
        """创建电机控制界面"""
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.serial_port = None
        self.running = False
        self.start_time = None  # 初始化开始时间属性

        # 串口选择与扫描按钮
        self.port_label = ttk.Label(frame, text="选择串口:")
        self.port_label.grid(row=0, column=0)
        self.port_combo = ttk.Combobox(frame)
        self.port_combo.grid(row=0, column=1)
        self.refresh_ports()

        self.refresh_button = ttk.Button(frame, text="扫描串口", command=self.refresh_ports)
        self.refresh_button.grid(row=0, column=2)

        # 波特率选择
        self.baudrate_label = ttk.Label(frame, text="波特率:")
        self.baudrate_label.grid(row=0, column=3)
        self.baudrate_combo = ttk.Combobox(frame, values=[2400, 9600, 19200, 38400, 57600, 115200], state="readonly")
        self.baudrate_combo.grid(row=0, column=4)
        self.baudrate_combo.set("19200")

        self.start_button = ttk.Button(frame, text="启动", command=self.start_serial)
        self.start_button.grid(row=0, column=5)

        # 创建步进值滑块和步进值显示
        self.step_label = ttk.Label(frame, text="步进值:")
        self.step_label.grid(row=1, column=0)
        self.step_slider = ttk.Scale(frame, from_=1, to=1000, orient='horizontal', command=self.update_step_display)
        self.step_slider.grid(row=1, column=1, columnspan=5)
        self.step_value_display = ttk.Label(frame, text="1")
        self.step_value_display.grid(row=1, column=6)

        # 创建轴选择按钮
        self.axis_buttons = []
        for i in range(4):
            btn = ttk.Button(frame, text=f'轴{i+1}', command=lambda i=i: self.select_axis(i))
            btn.grid(row=3, column=i)
            self.axis_buttons.append(btn)

        self.selected_axis = None

        # 创建控制按钮
        # 创建并布局“正转”按钮
        self.forward_button = ttk.Button(frame, text='正转', command=lambda: self.rotate_axis(True))
        self.forward_button.grid(row=4, column=0, columnspan=2)

        # 创建并布局“反转”按钮
        self.backward_button = ttk.Button(frame, text='反转', command=lambda: self.rotate_axis(False))
        self.backward_button.grid(row=4, column=2, columnspan=2)

        # 添加文本输入框
        self.input_text = ttk.Entry(frame)
        self.input_text.grid(row=5, column=0, columnspan=6, padx=10, pady=10)

        # 添加发送按钮
        self.send_button = ttk.Button(frame, text='发送', command=self.send_serial)
        self.send_button.grid(row=5, column=6, columnspan=2)

        # 文本框用于显示串口数据
        self.serial_output_text = tk.Text(frame, height=15, width=50)
        self.serial_output_text.grid(row=6, column=0, columnspan=8, padx=10, pady=10)
        # 创建步进速度滑块和步进速度显示标签
        self.speed_label = ttk.Label(frame, text="步进速度:")
        self.speed_label.grid(row=2, column=0)
        self.speed_slider = ttk.Scale(frame, from_=400, to=1000 , orient='horizontal', command=self.update_speed_display)
        self.speed_slider.grid(row=2, column=1, columnspan=5)
        self.speed_value_display = ttk.Label(frame, text="100")
        self.speed_value_display.grid(row=2, column=6)

        # 版权信息标签
        self.footer_label = ttk.Label(frame, text="Copyright © 2024 孙佩东. All Rights Reserved.", background="gray", foreground="white")  
        self.footer_label.grid(row=7, column=0, columnspan=8, sticky="ew", pady=(10,0))

        # 设置行列权重以自适应窗口大小
        for i in range(8):
            frame.columnconfigure(i, weight=1)
        for i in range(7):
            frame.rowconfigure(i, weight=1)

    def switch_mode(self, event=None):
        """切换界面模式"""
        if self.mode_var.get() == "motor_control":
            self.motor_control_frame.grid()
            self.preset_program_frame.grid_remove()
            self.program_editing_frame.grid_remove()
        elif self.mode_var.get() == "preset_program":
            self.motor_control_frame.grid_remove()
            self.preset_program_frame.grid()
            self.program_editing_frame.grid_remove()
        elif self.mode_var.get() == "program_editing":
            self.motor_control_frame.grid_remove()
            self.preset_program_frame.grid_remove()
            self.program_editing_frame.grid()
    def update_speed_display(self, value):
        """更新步进速度值显示"""
        self.speed_value_display.config(text=f"{float(value):.2f}")

    def create_preset_program_ui(self, frame):
        """创建预设程序界面"""
        self.select_file_button = ttk.Button(frame, text="选择JOSN文件", command=self.select_program_file)
        self.select_file_button.grid(row=0, column=0, padx=10, pady=10)
        # 开始执行按钮
        self.btn_execute = ttk.Button(frame, text="开始执行", command=self.execute_program)
        self.btn_execute.grid(row=0, column=1, padx=10, pady=10)
        self.serial_return_text_preset = tk.Text(frame,height=15, width=50)
        self.serial_return_text_preset.grid(row=1, column=0, columnspan=8, padx=10, pady=10)

        # 版权信息标签
        self.footer_label = ttk.Label(frame, text="Copyright © 2024 孙佩东. All Rights Reserved.", background="gray", foreground="white")
        self.footer_label.grid(row=6, column=0, columnspan=8, sticky="ew", pady=(10, 0))

        # 设置行列权重以自适应窗口大小
        for i in range(8):
            frame.columnconfigure(i, weight=1)
        for i in range(7):
            frame.rowconfigure(i, weight=1)

    def select_program_file(self):
        """选择程序文件并加载指令"""
        self.file_path = filedialog.askopenfilename(title="选择程序文件", filetypes=[("JSON Files", "*.json")])
        if self.file_path:
            self.program_data = self.load_instructions(self.file_path)
            self.serial_return_text_preset.insert(tk.END, f"选定文件: {self.file_path}\n")

    def load_instructions(self, file_path):
        """从文件中加载指令列表"""
        with open(file_path, 'r') as file:
            return json.load(file)
            
    def execute_program(self):
        """异步执行程序并更新GUI"""
        if not self.program_data:
            self.serial_return_text_preset.insert(tk.END, "程序数据为空，请先加载程序。\n")
            return
        
        self.serial_return_text_preset.delete('1.0', tk.END)
        self.serial_return_text_preset.insert(tk.END, "开始执行程序...\n")
        threading.Thread(target=self.execute_program_instructions, args=(self.program_data,), daemon=True).start()

    def execute_program_instructions(self, program_data):
        try:
            """在新线程中执行程序指令"""
            self.start_time = time.time()
            for instruction in sorted(program_data, key=lambda x: x['time']):
                while time.time() - self.start_time < instruction['time']:
                    time.sleep(0.01)

                axis = instruction['axis']
                angle = instruction['angle']
                spd = instruction['spd']
                motor1 = axis + 1
                motor2 = motor1 + 4
                command1 = f"{motor1}{'+' if angle >= 0 else ''}{angle},{spd:.2f}"
                command2 = f"{motor2}{'-' if angle >= 0 else '+'}{abs(angle)},{spd:.2f}"

                # 发送命令
                self.send_and_log(f"{command1}/{command2}")
        # 所有指令执行完毕后，在 GUI 中显示信息
            self.master.after(0, lambda: self.serial_return_text_preset.insert(tk.END, "所有指令执行完毕\n"))
        except Exception as e:
        # 如果出现错误，将错误信息输出到 GUI
            error_msg = f"执行指令时出现错误: {str(e)}"
            self.serial_return_text_preset.insert(tk.END, error_msg)




    def create_program_editing_ui(self, frame):
        """创建程序编辑界面"""
        self.program_text = tk.Text(frame, height=10)
        self.program_text.grid(row=0, column=0, columnspan=4, padx=10, pady=10)
        self.program_text.insert(tk.END, "输入程序指令\n格式为：时间(秒),轴,角度,速度\n例如：2,1,90,100\n5,2,-45,100")

        self.generate_program_button = ttk.Button(frame, text="生成JSON", command=self.generate_program)
        self.generate_program_button.grid(row=1, column=1, padx=10, pady=10)

        self.program_output = tk.Text(frame, height=15, width=50)
        self.program_output.grid(row=2, column=0, columnspan=4, padx=10, pady=10)

        # 添加文件名编辑框和保存按钮
        self.file_name_entry = ttk.Entry(frame, width=30)
        self.file_name_entry.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

        self.save_program_button = ttk.Button(frame, text="保存JSON文件", command=self.save_program_file)
        self.save_program_button.grid(row=3, column=3, padx=10, pady=10)

            # 轴选择按钮
        self.axis_var = tk.IntVar()
        for i in range(4):
            btn = ttk.Radiobutton(frame, text=f"轴{i+1}", variable=self.axis_var, value=i)
            btn.grid(row=5, column=i, padx=5, pady=5)

        # 时间、速度和角度的滑块
        self.time_scale = tk.Scale(frame, from_=0, to=120, orient=tk.HORIZONTAL, label="时间")
        self.time_scale.grid(row=6, column=0, columnspan=2, sticky="ew")
        self.speed_scale = tk.Scale(frame, from_=100, to=1000, resolution=0.01, orient=tk.HORIZONTAL, label="速度")
        self.speed_scale.grid(row=6, column=2, columnspan=2, sticky="ew")
        self.angle_scale = tk.Scale(frame, from_=-90, to=90, orient=tk.HORIZONTAL, label="角度")
        self.angle_scale.grid(row=7, column=0, columnspan=2, sticky="ew")

        # 左右双选按钮
        self.direction = tk.StringVar(value="+")
        self.toggle_button = ttk.Button(frame, text="+", command=self.toggle_direction)
        self.toggle_button.grid(row=7, column=2)

        # 输出单行JSON到编辑界面的按钮
        self.add_line_button = ttk.Button(frame, text="添加指令", command=self.add_line_to_program)
        self.add_line_button.grid(row=4, column=3)
        # 从单行JSON到完整josn生成的按钮
        self.generate_program_button = ttk.Button(frame, text="生成整体程序JSON", command=self.generate_line_program)
        self.generate_program_button.grid(row=4, column=1, padx=10, pady=10)
        # 版权信息标签
        self.footer_label = ttk.Label(frame, text="Copyright © 2024 孙佩东. All Rights Reserved.", background="gray", foreground="white")
        self.footer_label.grid(row=8, column=0, columnspan=8, sticky="ew", pady=(10, 0))
    def toggle_direction(self):
            current_value = self.direction.get()
            new_value = "-" if current_value == "+" else "+"
            self.direction.set(new_value)
            self.toggle_button.config(text=new_value)

    def add_line_to_program(self):
        """向 program_output 添加单行JSON数据"""
        time = self.time_scale.get()
        speed = self.speed_scale.get()
        angle = self.angle_scale.get() * (1 if self.direction.get() == "+" else -1)
        axis = self.axis_var.get() + 1  # 轴编号从1开始

        line_dict = {"time": time, "axis": axis, "angle": angle, "spd": speed}
        line_json = json.dumps(line_dict)
        self.program_output.insert(tk.END, line_json + "\n")

    def generate_line_program(self):
        """从 program_output 中的JSON字符串生成整体程序文档"""
        program_lines = self.program_output.get("1.0", tk.END).strip().split("\n")
        program_data = []
        
        for line in program_lines:
            try:
                line_dict = json.loads(line)  # 直接解析JSON字符串
                program_data.append(line_dict)
            except json.JSONDecodeError:
                continue  # 跳过无法解析的行

        program_data.sort(key=lambda x: x["time"])  # 根据时间排序
        program_document = json.dumps(program_data, indent=4)

        self.program_output.delete("1.0", tk.END)  # 清空当前内容
        self.program_output.insert(tk.END, program_document)  # 显示整理后的程序JSON

    def generate_program(self):
        """生成程序文档"""
        program_lines = self.program_text.get("1.0", tk.END).strip().split("\n")
        program_data = []
       
        for line in program_lines:
            parts = line.split(",")
            if len(parts) == 4:
                try:
                    time, axis, angle, spd = map(float, parts)
                    time, axis = int(time), int(axis)
                    angle = int(angle)
                    program_data.append({"time": time, "axis": axis, "angle": angle, "spd": spd})
                except ValueError:
                    continue  # Skip invalid lines

        program_data.sort(key=lambda x: x["time"])
        program_document = json.dumps(program_data, indent=4)

        self.program_output.delete("1.0", tk.END)
        self.program_output.insert(tk.END, program_document)

    def save_program_file(self):
        """保存程序文件"""
        file_name = self.file_name_entry.get()
        if file_name:
            file_path = filedialog.asksaveasfilename(defaultextension=".json", initialfile=file_name, filetypes=[("JSON Files", "*.json")])
            if file_path:
                with open(file_path, 'w') as file:
                    file.write(self.program_output.get("1.0", tk.END))

    def refresh_ports(self):
        """刷新可用串口列表"""
        ports = list_ports.comports()
        self.port_combo['values'] = [port.device for port in ports]

    def start_serial(self):
        """启动串口通信"""
        if self.serial_port:
            self.running = False
            if self.thread:  # 检查线程是否存在
                self.thread.join()
            self.serial_port.close()
            self.serial_port = None
        selected_port = self.port_combo.get()
        selected_baudrate = self.baudrate_combo.get()
        if selected_port:
            self.serial_port = serial.Serial(selected_port, baudrate=int(selected_baudrate), timeout=1)
            self.running = True
            self.thread = threading.Thread(target=self.listen_serial)
            self.thread.start()
    def select_axis(self, index):
        """选择要操作的轴"""
        self.selected_axis = index
        self.send_and_log(f"轴 {index+1}")

    def rotate_axis(self, clockwise):
        """旋转轴"""
        if self.selected_axis is not None:
            steps = int(self.step_slider.get())
            steps = int(self.step_slider.get())
            speed = self.speed_slider.get()  # 获取当前速度
            # 根据选中轴和旋转方向来确定正转和反转电机
            motor1 = self.selected_axis + 1
            motor2 = motor1 + 4  # 反转电机编号
            direction1 = '+' if clockwise else '-'  # 正转电机的旋转方向
            direction2 = '-' if clockwise else '+'  # 反转电机的旋转方向
            # 合并两个指令并发送
            combined_command = f"{motor1}{direction1}{steps},{speed:.2f}/{motor2}{direction2}{steps},{speed:.2f}"
            self.send_and_log(combined_command)

    def update_step_display(self, value):
        """更新步进值显示"""
        self.step_value_display.config(text=f"{int(float(value))}")

    def listen_serial(self):
        """监听串口数据"""
        while self.running:
            if self.serial_port.in_waiting:
                data = self.serial_port.readline().decode().strip()
                self.log_message(f"接收: {data}")  # 显示接收到的数据
                self.master.after(0, self.log_message, f"接收: {data}")  # 在主线程更新文本框

    def send_serial(self):
        text = self.input_text.get()  # 获取输入框中的文本
        self.send_and_log(text)  # 发送文本到串口

    def send_and_log(self, message):
        """发送数据并记录消息，包括步进速度"""

        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write((message + "\r\n").encode())  # 将完整命令发送到串口

    def log_message(self, message):
        """记录消息到日志"""
        self.serial_output_text.insert(tk.END, message + "\n")
        self.serial_output_text.see(tk.END)

    def send_and_log_preset(self, message):
        """发送数据并记录日志（用于预设程序界面）"""
        self.log_message_preset(message)  # 在GUI中显示消息
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write((message + "\r\n").encode())  # 向串口发送数据，确保以回车结尾

    def log_message_preset(self, message):
        """记录消息到日志（用于预设程序界面）"""
        self.serial_return_text_preset.insert(tk.END, message + "\n")
        self.serial_return_text_preset.see(tk.END)

    def on_closing(self):
        """处理应用关闭事件"""
        # 停止所有后台线程
        if hasattr(self, 'running') and self.running:
            self.running = False
            for thread in self.program_threads:
                if thread.is_alive():
                    thread.join()

        if hasattr(self, 'serial_port') and self.serial_port:
            self.serial_port.close()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MotorControlApp(root)
    root.mainloop()

    # 当GUI关闭时，确保后台线程也被正确关闭
    if app.running:
        app.running = False
        if app.thread:  # 检查线程是否存在
            app.thread.join()
    if app.serial_port:
        app.serial_port.close()
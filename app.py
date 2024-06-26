from flask import Flask, request, render_template, jsonify, url_for, make_response, redirect, flash
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objs as go
import os
import taichi as ti
import sympy as sp
import latex2sympy2
import subprocess
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

from config import get_timestamp
from mpl_toolkits.mplot3d import Axes3D
from latex2sympy2 import latex2sympy, latex2latex
from sympy import solve as solving, latex, sympify, Matrix, re
from matplotlib import pyplot as plt
from re import findall, split, MULTILINE

ti.init(arch=ti.cpu)

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host='47.76.200.188',   # 数据库的 IP 地址或域名
        user='Cat',  # 数据库用户名
        password='123234',  # 数据库密码
        database='numpdevis'  # 数据库名
    )

def str_to_function(expr_str, dim, dw, len1=None, len2=None, len3=None):
    """
    将 LaTeX 字符串形式的数学表达式转换为 Sympy 表达式，并根据维度返回计算后的数值列表。
    """
    # 将 LaTeX 字符串转换为 Sympy 表达式
    expr = latex2sympy2.latex2sympy(expr_str)

    # 定义符号
    x = sp.symbols('x')
    y = sp.symbols('y')
    z = sp.symbols('z')

    if dim == 1:
        f = [expr.subs(x, i * dw[1]).evalf() for i in range(int(len1 / dw[1]))]
        return f
    elif dim == 2:
        f = [[expr.subs({x: i * dw[1], y: j * dw[2]}).evalf() for j in range(int(len2 / dw[2]))] for i in
             range(int(len1 / dw[1]))]
        return f

class calculator_normal():
    def __init__(self, latex_string = None,model = None):
        self.func_strings = []
        self.func_strings.append(latex_string)
        # self.model = model

    def solve_non_equations(self,latex_text, formatter='latex'):
        regex = r"\\begin{cases}([\s\S]*)\\end{cases}"
        matches = findall(regex, latex_text, MULTILINE)
        equations = []
        if matches:
            matches = split(r"\\\\(?:\[?.*?\])?", matches[0])
            for match in matches:
                ins = latex2sympy(match)
                if type(ins) == list:
                    equations.extend(ins)
                else:
                    equations.append(ins)
            solved = solving(equations)
        else:
            return False
        if formatter == 'latex':
            print(latex(solved))
            return latex(solved)
        else:
            return solved
    def add_string(self,string):
        self.func_strings.append(string)

    def nonlinear_equation_solver(self,string):
        x = sp.symbols('x')
        equation = latex2sympy2.latex2sympy(string)
        derivative = sp.diff(equation, x)

        f = sp.lambdify(x, equation, "numpy")
        f_prime = sp.lambdify(x, derivative, "numpy")

        roots = []
        num_guesses = 10
        tolerance = 1e-10
        max_iterations = 1000
        unique_tolerance = 1e-5

        for _ in range(num_guesses):
            x_n = np.random.uniform(-100, 100)
            iteration = 0

            while True:
                f_prime_val = f_prime(x_n)
                if abs(f_prime_val) < tolerance:  # 避免除以零
                    break
                x_n1 = x_n - f(x_n) / f_prime_val
                if abs(x_n1 - x_n) < tolerance or iteration >= max_iterations:
                    # 检查新解是否与已找到的解足够不同
                    if not any(abs(x_n1 - root) < unique_tolerance for root in roots):
                        roots.append(x_n1)
                    break
                x_n = x_n1
                iteration += 1
        # print(roots)
        # return roots
        formatted_roots = [round(root, 2) for root in roots]
        formatted_roots_latex = [latex2sympy2.latex(root) for root in formatted_roots]
        print(formatted_roots_latex)
        return formatted_roots_latex

    def cal_func_dri(self,str_f_expr):
        """
        计算一元函数的导数并返回一个可调用的Python函数

        参数:
        - f_expr: sympy表达式，表示一元函数
        - x: sympy符号，表示函数的变量

        返回:
        - 导数的Python函数
        """
        # 计算导数
        f_expr = latex2sympy(str_f_expr)
        x = sp.symbols('x')
        f_prime_expr = sp.diff(f_expr, x)

        # 将符号表达式转换为可调用的Python函数
        f_prime_func = sp.lambdify(x, f_prime_expr, 'numpy')
        print(latex2sympy2.latex(f_prime_func))
        return latex2sympy2.latex(f_prime_func)
    def find_extreme(self,str_f_expr):
        """
        计算一元函数的极值点

        参数:
        - f_expr: sympy表达式，表示一元函数
        - x: sympy符号，表示函数的变量

        返回:
        - 极值点列表
        """
        # 计算一阶导数
        f_expr = latex2sympy(str_f_expr)
        x = sp.symbols('x')
        f_prime = sp.diff(f_expr, x)

        # 解一阶导数等于0的方程，找到可能的极值点
        critical_points = sp.solve(f_prime, x)

        # （可选）计算二阶导数并检查每个临界点
        f_double_prime = sp.diff(f_prime, x)
        for point in critical_points:
            # 二阶导数检验
            if f_double_prime.subs(x, point) > 0:
                print(f"{point} 是极小值点")
            elif f_double_prime.subs(x, point) < 0:
                print(f"{point} 是极大值点")
            else:
                print(f"{point} 是鞍点")

        print(latex2sympy2.latex(critical_points))
        return latex2sympy2.latex(critical_points)
    def solve_integral(self,string):
        try:
            # 使用latex2sympy2将LaTeX字符串转换为sympy表达式
            expression = latex2sympy2.latex2sympy(string)
            # 定义变量x
            x = sp.symbols('x')

            # 检查表达式是否为定积分（有边界）
            if isinstance(expression, sp.Integral):
                if len(expression.limits) == 1 and len(expression.limits[0]) == 3:
                    # 提取积分变量和积分区间（定积分）
                    _, a, b = expression.limits[0]
                    solution = sp.integrate(expression.function, (x, a, b))
                else:
                    # 处理不定积分
                    solution = expression.doit()
                    solution = latex2sympy2.latex(solution)
            else:
                # 若表达式不是积分，则直接返回
                return "表达式不是一个积分"
            print(solution)
            return solution
        except Exception as e:
            # 处理可能出现的任何异常，并返回错误信息
            return f"发生错误: {str(e)}"


    def normal_solve(self,string):
        func = latex2sympy2.latex2sympy(string)
        # func.evalf
        return str(func.evalf())

    # \=\\
    def calculate_matrix(self,latex_str):
        # 将 LaTeX 字符串转换为 SymPy 表达式
        expr = latex2sympy(latex_str)

        # 假设转换后的表达式是一个矩阵求和操作
        # 计算这个表达式
        result = expr.doit()
        result = latex2sympy2.latex(result)
        return result

    from latex2sympy2 import latex2sympy
    from sympy import Eq, solve, symbols

    def solve_linear_system_from_latex(self,str_A,str_b):
        # 解析 LaTeX 字符串
        A = latex2sympy(str_A)
        b = latex2sympy(str_b)
        n = A.shape[1]  # A的列数
        X_symbols = sp.symbols(f'x1:{n + 1}')  # 创建n个符号变量

        # 使用linsolve求解
        solution = sp.linsolve((A, b), X_symbols)
        return latex2sympy2.latex(solution)

    def inverse_matrix(self,A_str):
        """
        返回给定SymPy矩阵对象A的逆矩阵。

        参数:
        - A: 一个SymPy矩阵对象。

        返回:
        - A的逆矩阵，如果存在的话；否则，如果A不可逆，抛出异常。
        """
        A = latex2sympy(A_str)
        # 检查A是否为方阵
        if A.shape[0] != A.shape[1]:
            raise ValueError("矩阵必须是方阵才能求逆。")

        # 检查A是否可逆（即行列式不为0）
        if A.det() == 0:
            raise ValueError("矩阵不可逆，因为其行列式为0。")

        # 返回逆矩阵
        return latex2sympy2.latex(A.inv())
    def plot_from_latex_multiple(self):
        plt.style.use('ggplot')  # 选择一个炫酷的图形样式
        plt.figure(figsize=(10, 6))  # 调整图形的大小

        # 定义变量 x
        x = sp.symbols('x')
        x_vals = np.linspace(-10, 10, 400)  # 定义 x 轴上的点

        for string in self.func_strings:
            expr = latex2sympy2.latex2sympy(string)
            f = sp.lambdify(x, expr, 'numpy')
            y_vals = f(x_vals)
            plt.plot(x_vals, y_vals, label='$' + sp.latex(expr) + '$', linestyle='-', linewidth=2)

        plt.fill_between(x_vals, 0, y_vals, color="skyblue", alpha=0.4)  # 添加填充效果
        plt.legend(loc='best')
        plt.grid(True)  # 显示网格
        plt.title('函数图像')  # 添加标题
        plt.xlabel('$x$')  # 添加 x 轴标签
        plt.ylabel('$f(x)$')  # 添加 y 轴标签
        plt.show()

    def draw_binary_func(self,str_f_expr):
        """
        绘制二元函数的等高线图。

        参数:
        - f_expr: sympy表达式，表示二元函数。
        - x_range: (min, max)形式的元组，定义x的范围。
        - y_range: (min, max)形式的元组，定义y的范围。
        - title: 图形的标题。
        """
        f_expr = latex2sympy(str_f_expr)
        # 定义符号变量
        x, y = sp.symbols('x y')

        # 将sympy表达式转换为可用于numpy的函数
        f_lambdified = sp.lambdify((x, y), f_expr, 'numpy')

        # 创建一个网格
        x_vals = np.linspace(-100, 100, 1000)
        y_vals = np.linspace(-100, 100, 1000)
        X, Y = np.meshgrid(x_vals, y_vals)

        # 在网格上计算函数值
        Z = f_lambdified(X, Y)

        # 绘制图形
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')

        # 绘制曲面图
        surf = ax.plot_surface(X, Y, Z, cmap='viridis', edgecolor='none')
        fig.colorbar(surf, shrink=0.5, aspect=5)  # 添加色彩条

        # 设置标题和轴标签
        ax.set_title("diagram")
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_zlabel('f(x, y)')

        # 显示图形
        plt.show()

    def solve_diff_equ(self,str_func):
        x = sp.symbols('x')
        f = sp.Function('f')
        func = latex2sympy(str_func)
        solve = sp.dsolve(func,f(x))
        return latex2sympy2.latex(solve)



    def exe_test(self):
        return self.cal_func_dri(self.func_strings[0])
    def solve_non_equations_exe(self):
        return self.solve_non_equations(self.func_strings[0])
    def solve_integral_exe(self):
        return self.solve_integral(self.func_strings[0])
    def calculate_matrix_exe(self):
        return self.calculate_matrix(self.func_strings[0])
    def nonlinear_equation_exe(self):
        return self.nonlinear_equation_solver(self.func_strings[0])
    def find_extreme_exe(self):
        return self.find_extreme(self.func_strings[0])
    def solve_linear_system_exe(self):
        return self.solve_linear_system_from_latex(self.func_strings[0], self.func_strings[1])
    def inverse_matrix_exe(self):
        return self.inverse_matrix(self.func_strings[0])
    def plot_from_latex_multiple_exe(self):
        self.plot_from_latex_multiple()
@ti.data_oriented
class wave_equ():
    def __init__(self, func1_string, func2_string, len, dim, v, dw, a, b, t):

        self.func1_string = func1_string
        self.func2_string = func2_string
        self.len = len
        self.dim = dim
        self.v = v
        self.dw = dw
        self.a = a
        self.b = b
        self.t = t


        # dim1
        self.phi_xt = ti.field(ti.f32, shape=(int(self.len[0] / self.dw[1]), int(self.t / self.dw[0])))
        self.func1_dim1 = ti.field(ti.f32, shape=int(self.len[0] / self.dw[1]))
        self.func2_dim1 = ti.field(ti.f32, shape=int(self.len[0] / self.dw[1]))
        # dim2
        self.phi_xyt = ti.field(ti.f32, shape=(
            int(self.len[0] / self.dw[1]), int(self.len[1] / self.dw[2]), int(self.t / self.dw[0])))
        self.func1_dim2 = ti.field(ti.f32, shape=(int(self.len[0] / self.dw[1]), int(self.len[1] / self.dw[2])))
        self.func2_dim2 = ti.field(ti.f32, shape=(int(self.len[0] / self.dw[1]), int(self.len[1] / self.dw[2])))
        # dim3
        self.phi_xyzt = ti.field(ti.f32, shape=(
            int(self.len[0] / self.dw[1]), int(self.len[1] / self.dw[2]), int(self.len[2] / self.dw[3]),
            int(self.t / self.dw[0])))
        self.func1_dim3 = ti.field(ti.f32, shape=(
            int(self.len[0] / self.dw[1]), int(self.len[1] / self.dw[2]), int(self.len[2] / self.dw[3])))
        self.func2_dim3 = ti.field(ti.f32, shape=(
            int(self.len[0] / self.dw[1]), int(self.len[1] / self.dw[2]), int(self.len[2] / self.dw[3])))

    @ti.func
    def get_phi_xyt(self):
        return self.phi_xyt

    def init_func(self):
        f1 = str_to_function(self.func1_string, self.dim, self.dw, self.len[0], self.len[1], self.len[2])
        f2 = str_to_function(self.func2_string, self.dim, self.dw, self.len[0], self.len[1], self.len[2])
        if self.dim == 1:
            for i in range(0, int(self.len[0] / self.dw[1])):
                # 确保赋值前将结果转换为float类型
                self.func1_dim1[i] = f1[i]
                self.func2_dim1[i] = f2[i]
        if self.dim == 2:
            for i in range(0, int(self.len[0] / self.dw[1])):
                for j in range(0, int(self.len[1] / self.dw[2])):
                    self.func1_dim2[i, j] = f1[i][j]
                    self.func2_dim2[i, j] = f2[i][j]

    @ti.kernel
    def wave_solver_dim1(self):
        # 初始化边界条件
        a1 = self.a[0]
        b1 = self.b[0]
        v = self.v
        t = self.t
        dt = self.dw[0]
        dx = self.dw[1]
        len = self.len[0]
        self.phi_xt[0, 0] = a1
        self.phi_xt[int(len / dx) - 1, 0] = b1

        # 设置初始条件
        for i in ti.ndrange((1, int(len / dx) - 1)):
            self.phi_xt[i, 0] = self.func1_dim1[i]  # 初始位移条件
            if i < int(len / dx) - 1:
                self.phi_xt[i, 1] = dt * self.func2_dim1[i] + self.phi_xt[i, 0]  # 初速度影响的近似

        # 迭代更新
        for k in ti.ndrange((1, 513)):
            # 重新应用边界条件
            self.phi_xt[0, k + 1] = a1
            self.phi_xt[int(len / dx) - 1, k + 1] = b1

            for i in ti.ndrange((1, int(len / dx) - 1)):
                self.phi_xt[i, k + 1] = 2 * self.phi_xt[i, k] - self.phi_xt[i, k - 1] + (v * v * dt * dt) / (
                        dx * dx) * (
                                                self.phi_xt[i - 1, k] - 2 * self.phi_xt[i, k] + self.phi_xt[i + 1, k])
        for k in ti.ndrange((513, int(t / dt) - 1)):
            # 重新应用边界条件
            self.phi_xt[0, k + 1] = a1
            self.phi_xt[int(len / dx) - 1, k + 1] = b1

            for i in ti.ndrange((1, int(len / dx) - 1)):
                self.phi_xt[i, k + 1] = 2 * self.phi_xt[i, k] - self.phi_xt[i, k - 1] + (v * v * dt * dt) / (
                        dx * dx) * (
                                                self.phi_xt[i - 1, k] - 2 * self.phi_xt[i, k] + self.phi_xt[i + 1, k])

    @ti.kernel
    def wave_solver_dim2(self):
        a1, a2 = self.a[0], self.a[1]  # 沿x和y的边界条件
        b1, b2 = self.b[0], self.b[1]  # 沿x和y的边界条件
        v = self.v
        dt = self.dw[0]
        dx = self.dw[1]
        dy = self.dw[2]
        len1, len2 = self.len[0], self.len[1]
        for i, j in ti.ndrange((0, int(len1 / dx) - 1), (0, int(len2 / dy) - 1)):
            self.phi_xyt[i, j, 0] = self.func1_dim2[i, j]
            self.phi_xyt[i, j, 1] = dt * self.func2_dim2[i, j] + self.phi_xyt[i, j, 0]
        # 边界条件初始化，对于二维情况，需要设置四边的边界
        for j in ti.ndrange((0, int(len2 / dy))):  # x方向的边界
            self.phi_xyt[0, j, 0] = a1
            self.phi_xyt[int(len1 / dx) - 1, j, 0] = b1
        for i in ti.ndrange((0, int(len1 / dx))):  # y方向的边界
            self.phi_xyt[i, 0, 0] = a2
            self.phi_xyt[i, int(len2 / dy) - 1, 0] = b2

        # 时间迭代
        for k in ti.ndrange((2, 513)):  # 从k=2开始，因为k=0和k=1已通过初始条件设置int(self.t / dt)
            for i, j in ti.ndrange((1, int(len1 / dx) - 1), (1, int(len2 / dy) - 1)):
                self.phi_xyt[i, j, k] = (2 * self.phi_xyt[i, j, k - 1] - self.phi_xyt[i, j, k - 2] +
                                         (v ** 2 * dt ** 2 / dx ** 2) * (
                                                 self.phi_xyt[i + 1, j, k - 1] - 2 * self.phi_xyt[i, j, k - 1] +
                                                 self.phi_xyt[i - 1, j, k - 1]) +
                                         (v ** 2 * dt ** 2 / dy ** 2) * (
                                                 self.phi_xyt[i, j + 1, k - 1] - 2 * self.phi_xyt[i, j, k - 1] +
                                                 self.phi_xyt[i, j - 1, k - 1]))

            # 更新边界条件以保持不变
            for j in ti.ndrange((0, int(len2 / dy))):  # x方向的边界
                self.phi_xyt[0, j, k] = a1
                self.phi_xyt[int(len1 / dx) - 1, j, k] = b1
            for i in ti.ndrange((0, int(len1 / dx))):  # y方向的边界
                self.phi_xyt[i, 0, k] = a2
                self.phi_xyt[i, int(len2 / dy) - 1, k] = b2
        for k in ti.ndrange((513, int(self.t / dt))):  # 从k=2开始，因为k=0和k=1已通过初始条件设置
            for i, j in ti.ndrange((1, int(len1 / dx) - 1), (1, int(len2 / dy) - 1)):
                self.phi_xyt[i, j, k] = (2 * self.phi_xyt[i, j, k - 1] - self.phi_xyt[i, j, k - 2] +
                                         (v ** 2 * dt ** 2 / dx ** 2) * (
                                                 self.phi_xyt[i + 1, j, k - 1] - 2 * self.phi_xyt[i, j, k - 1] +
                                                 self.phi_xyt[i - 1, j, k - 1]) +
                                         (v ** 2 * dt ** 2 / dy ** 2) * (
                                                 self.phi_xyt[i, j + 1, k - 1] - 2 * self.phi_xyt[i, j, k - 1] +
                                                 self.phi_xyt[i, j - 1, k - 1]))

            # 更新边界条件以保持不变
            for j in ti.ndrange((0, int(len2 / dy))):  # x方向的边界
                self.phi_xyt[0, j, k] = a1
                self.phi_xyt[int(len1 / dx) - 1, j, k] = b1
            for i in ti.ndrange((0, int(len1 / dx))):  # y方向的边界
                self.phi_xyt[i, 0, k] = a2
                self.phi_xyt[i, int(len2 / dy) - 1, k] = b2

    def print_field_dim1(self):
        for i, j in ti.ndrange((0, int(self.len[0] / self.dw[1])), (0, int(self.t / self.dw[0]))):
            print(f"x[{i}, {j}] = {self.phi_xt[i, j]}")  # 打印field的每个元素

    def print_field_dim2(self):
        for i, j, k in ti.ndrange((0, int(self.len[0] / self.dw[1])), (0, int(self.len[1] / self.dw[2])),
                                  (0, int(self.t / self.dw[0]))):
            print(f"x[{i}, {j},{k}] = {self.phi_xyt[i, j, k]}")  # 打印field的每个元素

    def save_data_dim1(self):
        data = self.phi_xt.to_numpy()
        np.save('wave_dim1_data.npy', data)

    def load_data_dim1(self):
        data = np.load('wave_dim1_data.npy')
        temp_phi_xt = ti.field(dtype=ti.f32, shape=data.shape)
        temp_phi_xt.from_numpy(data)
        self.phi_xt = temp_phi_xt

    def save_data_dim2(self):
        data = self.phi_xyt.to_numpy()
        np.save('wave_dim2_data.npy', data)

    def load_data_dim2(self):
        data = np.load('wave_dim2_data.npy')
        temp_phi_xyt = ti.field(dtype=ti.f32, shape=data.shape)
        temp_phi_xyt.from_numpy(data)
        self.phi_xyt = temp_phi_xyt

    def draw_dim1(self):
        dx = self.dw[1]
        dt = self.dw[0]
        len1 = self.len[0]
        t = self.t
        len_points = int(len1 / dx)
        time_points = int(t / dt)
        data_ti = self.phi_xt
        gui = ti.GUI("弦振动动画", res=(800, 600))
        for i, j in ti.ndrange((0, int(self.len[0] / self.dw[1])), (0, int(self.t / self.dw[0]))):
            data_ti[i, j] = data_ti[i, j] + 15
            print(int(self.len[0] / self.dw[1]) - i)
        max_value = max(data_ti.to_numpy().flatten())  # 提前计算最大值以提高效率

        for t in range(time_points):
            if t == 100:
                break
            pos = []
            for i in range(len_points):
                # 假设 data_ti 中存储的y值需要被适当缩放和位移以适配GUI的显示范围
                x = i / len_points  # 将 x 坐标标准化到 [0, 1]
                y = data_ti[i, t] / max_value  # 将 y 值归一化
                pos.append([x, y])
            pos_np = np.array(pos)  # 将 pos 列表转换为 numpy 数组
            gui.circles(pos_np, radius=2, color=0x068587)
            gui.show(str(t) + '.png')
        subprocess.run(['python', 'Record_wave.py'], check=True)

    def draw_dim2(self):
        Nx = int(self.len[0] / self.dw[1])  # 网格大小
        Ny = int(self.len[1] / self.dw[2])
        dx = self.dw[1]  # 网格间距
        dy = self.dw[2]
        dt = self.dw[0]  # 时间步长

        # Taichi变量
        scalar = ti.field
        height = scalar(dtype=ti.f32, shape=(Nx, Ny))
        velocity = scalar(dtype=ti.f32, shape=(Nx, Ny))
        colors = ti.Vector.field(3, dtype=ti.f32, shape=(Nx, Ny))

        # 粒子位置和颜色（一维表示）
        particles_pos = ti.Vector.field(3, dtype=ti.f32, shape=(Nx * Ny))
        particles_color = ti.Vector.field(3, dtype=ti.f32, shape=(Nx * Ny))

        # 初始化波动
        @ti.kernel
        def initialize_wave():
            for i, j in ti.ndrange(Nx, Ny):
                height[i, j] = self.phi_xyt[i, j, 0]

        # 更新波动方程
        @ti.kernel
        def update_wave(t: ti.f32):
            for i, j in ti.ndrange((1, Nx - 1), (1, Ny - 1)):  # 分别为i和j维度设置范围
                height[i, j] = self.phi_xyt[i, j, int(t)]

        # 将波动高度数据转换为颜色
        @ti.kernel
        def fill_colors():
            for i, j in height:
                if (i // 32 + j // 32) % 2 == 0:  # 调整间隔大小以适应粒子的密度
                    colors[i, j] = ti.Vector([0.22, 0.72, 0.52])
                else:
                    colors[i, j] = ti.Vector([1, 0.334, 0.52])

        # 二维转一维
        @ti.kernel
        def flatten_fields():
            for i, j in ti.ndrange(Nx, Ny):
                idx = i * Nx + j
                particles_pos[idx] = ti.Vector([i * dx - 0.5, height[i, j], j * dy - 0.5])
                particles_color[idx] = colors[i, j]

        window = ti.ui.Window('2D Wave Equation', (800, 800))
        canvas = window.get_canvas()
        canvas.set_background_color((1, 1, 1))
        scene = window.get_scene()
        # 设置摄像机
        camera = ti.ui.make_camera()
        camera.position(-15, 15, 0)
        camera.lookat(2, 0, 2)
        camera.fov(20)
        initialize_wave()
        t = 0

        while window.running:
            if t == 100:
                break
            t = t + 1
            update_wave(t)

            fill_colors()
            flatten_fields()  # 更新粒子位置和颜色

            camera.track_user_inputs(window, movement_speed=0.03, hold_key=ti.ui.LMB)

            scene.set_camera(camera)

            # 设置点光源和环境光源
            scene.point_light(pos=(1, 2, 2), color=(0.8, 0.8, 1))  # 调整光源颜色为偏蓝色调
            scene.ambient_light((0.2, 0.2, 0.6))  # 调整环境光为偏蓝色调
            # 使用颜色渲染场景
            scene.particles(particles_pos, radius=0.02, per_vertex_color=particles_color)  # 可以调整粒子半径
            print(particles_pos)
            # 渲染场景
            canvas.scene(scene)
            window.save_image(str(t) + '.png')
            window.show()
        subprocess.run(['python', 'Record_wave.py'], check=True)

@ti.data_oriented
class height_equ():
    def __init__(self, func_string, len, dim, v, dw, a, b, t):
        self.func_string = func_string
        self.len = len
        self.dim = dim
        self.v = v
        self.dw = dw
        self.a = a
        self.b = b
        self.t = t
        # dim1
        self.phi_xt = ti.field(ti.f32, shape=(int(self.len[0] / self.dw[1]), int(self.t / self.dw[0])))
        self.func_dim1 = ti.field(ti.f32, shape=int(self.len[0] / self.dw[1]))
        # dim2
        self.phi_xyt = ti.field(ti.f32, shape=(
        int(self.len[0] / self.dw[1]), int(self.len[1] / self.dw[2]), int(self.t / self.dw[0])))
        self.func_dim2 = ti.field(ti.f32, shape=(int(self.len[0] / self.dw[1]), int(self.len[1] / self.dw[2])))
        # dim3
        self.phi_xyzt = ti.field(ti.f32, shape=(
        int(self.len[0] / self.dw[1]), int(self.len[1] / self.dw[2]), int(self.len[2] / self.dw[3]),
        int(self.t / self.dw[0])))
        self.func_dim3 = ti.field(ti.f32, shape=(
        int(self.len[0] / self.dw[1]), int(self.len[1] / self.dw[2]), int(self.len[2] / self.dw[3])))

    def init_func(self):
        f1 = str_to_function(self.func_string, self.dim, self.dw, self.len[0], self.len[1], self.len[2])
        if self.dim == 1:
            for i in range(0, int(self.len[0] / self.dw[1])):
                # 确保赋值前将结果转换为float类型
                self.func_dim1[i] = f1[i]
        if self.dim == 2:
            for i in range(0, int(self.len[0] / self.dw[1])):
                for j in range(0, int(self.len[1] / self.dw[2])):
                    self.func_dim2[i, j] = f1[i][j]
        if self.dim == 3:
            for i in range(0, int(self.len[0] / self.dw[1])):
                for j in range(0, int(self.len[1] / self.dw[2])):
                    for k in range(0, int(self.len[2] / self.dw[3])):
                        self.func_dim3[i, j, k] = f1[i][j][k]

    @ti.kernel
    def height_solver_dim1(self):
        # 初始化边界条件
        a1 = self.a[0]
        b1 = self.b[0]
        v = self.v
        t = self.t
        dt = self.dw[0]
        dx = self.dw[1]
        len1 = self.len[0]
        self.phi_xt[0, 0] = a1
        self.phi_xt[int(len1 / dx) - 1, 0] = b1
        for i in ti.ndrange((1, int(len1 / dx) - 1)):
            self.phi_xt[i, 0] = self.func_dim1[i]  # 初始位移条件
        for n in ti.ndrange((0, 513)):  # 假设 self.t 是总时间步数
            self.phi_xt[0, n + 1] = a1
            self.phi_xt[int(len1 / dx) - 1, n + 1] = b1
            for i in ti.ndrange((1, int(len1 / dx) - 1)):
                self.phi_xt[i, n + 1] = self.phi_xt[i, n] + v * dt / (dx ** 2) * (
                        self.phi_xt[i + 1, n] - 2 * self.phi_xt[i, n] + self.phi_xt[i - 1, n])
        for n in ti.ndrange((513, int(t / dt) - 1)):  # 假设 self.t 是总时间步数
            self.phi_xt[0, n + 1] = a1
            self.phi_xt[int(len1 / dx) - 1, n + 1] = b1
            for i in ti.ndrange((1, int(len1 / dx) - 1)):
                self.phi_xt[i, n + 1] = self.phi_xt[i, n] + v * dt / (dx ** 2) * (
                        self.phi_xt[i + 1, n] - 2 * self.phi_xt[i, n] + self.phi_xt[i - 1, n])

    @ti.kernel
    def height_solver_dim2(self):
        a1, a2 = self.a[0], self.a[1]  # 沿x和y的边界条件
        b1, b2 = self.b[0], self.b[1]  # 沿x和y的边界条件
        v = self.v
        dt = self.dw[0]
        dx = self.dw[1]
        dy = self.dw[2]
        t = self.t
        len1, len2 = self.len[0], self.len[1]
        for i, j in ti.ndrange((0, int(len1 / dx) - 1), (0, int(len2 / dy) - 1)):
            self.phi_xyt[i, j, 0] = self.func_dim2[i, j]
        # 边界条件初始化，对于二维情况，需要设置四边的边界
        for j in ti.ndrange((0, int(len2 / dy))):  # x方向的边界
            self.phi_xyt[0, j, 0] = a1
            self.phi_xyt[int(len1 / dx) - 1, j, 0] = b1
        for i in ti.ndrange((0, int(len1 / dx))):  # y方向的边界
            self.phi_xyt[i, 0, 0] = a2
            self.phi_xyt[i, int(len2 / dy) - 1, 0] = b2
            # 迭代更新
        for n in ti.ndrange((0, 511)):  # 假设 self.t 是总时间步数int(t / dt) - 1)
            for i, j in ti.ndrange((1, int(len1 / dx) - 1), (1, int(len2 / dy) - 1)):
                self.phi_xyt[i, j, n + 1] = self.phi_xyt[i, j, n] + v * dt / (dx ** 2) * (
                        self.phi_xyt[i + 1, j, n] +
                        self.phi_xyt[i - 1, j, n] +
                        self.phi_xyt[i, j + 1, n] +
                        self.phi_xyt[i, j - 1, n] -
                        4 * self.phi_xyt[i, j, n]
                )
            # 更新边界条件以保持不变
            for j in ti.ndrange((0, int(len2 / dy))):  # x方向的边界
                self.phi_xyt[0, j, n] = a1
                self.phi_xyt[int(len1 / dx) - 1, j, n] = b1
            for i in ti.ndrange((0, int(len1 / dx))):  # y方向的边界
                self.phi_xyt[i, 0, n] = a2
                self.phi_xyt[i, int(len2 / dy) - 1, n] = b2
        for n in ti.ndrange((511,1024)):  # 假设 self.t 是总时间步数
            for i, j in ti.ndrange((1, int(len1 / dx) - 1), (1, int(len2 / dy) - 1)):
                self.phi_xyt[i, j, n + 1] = self.phi_xyt[i, j, n] + v * dt / (dx ** 2) * (
                        self.phi_xyt[i + 1, j, n] +
                        self.phi_xyt[i - 1, j, n] +
                        self.phi_xyt[i, j + 1, n] +
                        self.phi_xyt[i, j - 1, n] -
                        4 * self.phi_xyt[i, j, n]
                )
            # 更新边界条件以保持不变
            for j in ti.ndrange((0, int(len2 / dy))):  # x方向的边界
                self.phi_xyt[0, j, n] = a1
                self.phi_xyt[int(len1 / dx) - 1, j, n] = b1
            for i in ti.ndrange((0, int(len1 / dx))):  # y方向的边界
                self.phi_xyt[i, 0, n] = a2
                self.phi_xyt[i, int(len2 / dy) - 1, n] = b2
        for n in ti.ndrange((1024,int(t / dt) - 1 )):  # 假设 self.t 是总时间步数
            for i, j in ti.ndrange((1, int(len1 / dx) - 1), (1, int(len2 / dy) - 1)):
                self.phi_xyt[i, j, n + 1] = self.phi_xyt[i, j, n] + v * dt / (dx ** 2) * (
                        self.phi_xyt[i + 1, j, n] +
                        self.phi_xyt[i - 1, j, n] +
                        self.phi_xyt[i, j + 1, n] +
                        self.phi_xyt[i, j - 1, n] -
                        4 * self.phi_xyt[i, j, n]
                )
            # 更新边界条件以保持不变
            for j in ti.ndrange((0, int(len2 / dy))):  # x方向的边界
                self.phi_xyt[0, j, n] = a1
                self.phi_xyt[int(len1 / dx) - 1, j, n] = b1
            for i in ti.ndrange((0, int(len1 / dx))):  # y方向的边界
                self.phi_xyt[i, 0, n] = a2
                self.phi_xyt[i, int(len2 / dy) - 1, n] = b2

    def save_data_dim1(self):
        data = self.phi_xt.to_numpy()
        np.save('height_dim1_data.npy',data)

    def load_data_dim1(self):
        data = np.load('height_dim1_data.npy')
        temp_phi_xt = ti.field(dtype=ti.f32, shape=data.shape)
        temp_phi_xt.from_numpy(data)
        self.phi_xt = temp_phi_xt
    def save_data_dim2(self):
        data = self.phi_xyt.to_numpy()
        np.save('height_dim2_data.npy',data)

    def load_data_dim2(self):
        data = np.load('height_dim2_data.npy')
        temp_phi_xyt = ti.field(dtype=ti.f32, shape=data.shape)
        temp_phi_xyt.from_numpy(data)
        self.phi_xyt = temp_phi_xyt
    def save_data_dim3(self):
        data = self.phi_xyzt.to_numpy()
        np.save('height_dim3_data.npy',data)

    def load_data_dim3(self):
        data = np.load('height_dim3_data.npy')
        temp_phi_xyzt = ti.field(dtype=ti.f32, shape=data.shape)
        temp_phi_xyzt.from_numpy(data)
        self.phi_xyzt = temp_phi_xyzt
    def print_field_dim1(self):
        for i, j in ti.ndrange((0, int(self.len[0] / self.dw[1])), (0, int(self.t / self.dw[0]))):
            print(f"x[{i}, {j}] = {self.phi_xt[i, j]}")  # 打印field的每个元素

    def print_field_dim2(self):
        for i, j, k in ti.ndrange((0, int(self.len[0] / self.dw[1])), (0, int(self.len[1] / self.dw[2])),
                                  (0, int(self.t / self.dw[0]))):
            print(f"x[{i}, {j},{k}] = {self.phi_xyt[i, j, k]}")  # 打印field的每个元素

    def print_field_dim3(self):
        for i, j, k, t in ti.ndrange((0, int(self.len[0] / self.dw[1])), (0, int(self.len[1] / self.dw[2])),
                                     (0, int(self.len[2] / self.dw[3])), (0, int(self.t / self.dw[0]))):
            print(f"x[{i}, {j},{k},{t}] = {self.phi_xyzt[i, j, k, t]}")  # 打印field的每个元素

    def draw_dim1(self):
        dx = self.dw[1]
        dt = self.dw[0]
        len1 = self.len[0]
        t = self.t
        len_points = int(len1 / dx)
        time_points = int(t / dt)
        data_ti = self.phi_xt
        gui = ti.GUI("弦振动动画", res=(800, 600))
        for i, j in ti.ndrange((0, int(self.len[0] / self.dw[1])), (0, int(self.t / self.dw[0]))):
            data_ti[i,j] = data_ti[i,j]+15
            print(int(self.len[0] / self.dw[1])-i)
        max_value = max(data_ti.to_numpy().flatten())  # 提前计算最大值以提高效率

        for t in range(time_points):

            if t == 100:
                break

            pos = []
            for i in range(len_points):
                # 假设 data_ti 中存储的y值需要被适当缩放和位移以适配GUI的显示范围
                x = i / len_points  # 将 x 坐标标准化到 [0, 1]
                y = data_ti[i, t] / max_value  # 将 y 值归一化
                pos.append([x, y])
            pos_np = np.array(pos)  # 将 pos 列表转换为 numpy 数组
            gui.circles(pos_np, radius=2, color=0x068587)
            gui.show(str(t) + '.png')
        subprocess.run(['python', 'Record_heat.py'], check=True)

    def draw_dim2(self):
        Nx = int(self.len[0] / self.dw[1])  # 网格大小
        Ny = int(self.len[1] / self.dw[2])
        dx = self.dw[1]  # 网格间距
        dy = self.dw[2]
        dt = self.dw[0]  # 时间步长
        result_dir = "./results"
        video_manager = ti.tools.VideoManager(output_dir=result_dir, framerate=24, automatic_build=False)

        # Taichi变量
        scalar = ti.field
        height = scalar(dtype=ti.f32, shape=(Nx, Ny))
        velocity = scalar(dtype=ti.f32, shape=(Nx, Ny))
        colors = ti.Vector.field(3, dtype=ti.f32, shape=(Nx, Ny))

        # 粒子位置和颜色（一维表示）
        particles_pos = ti.Vector.field(3, dtype=ti.f32, shape=(Nx * Ny))
        particles_color = ti.Vector.field(3, dtype=ti.f32, shape=(Nx * Ny))

        # 初始化波动
        @ti.kernel
        def initialize_wave():
            for i, j in ti.ndrange(Nx, Ny):
                height[i, j] = self.phi_xyt[i, j, 0]

        # 更新波动方程
        @ti.kernel
        def update_wave(t: ti.f32):
            for i, j in ti.ndrange((1, Nx - 1), (1, Ny - 1)):  # 分别为i和j维度设置范围
                height[i, j] = self.phi_xyt[i, j, int(t)]

        # 将波动高度数据转换为颜色
        @ti.kernel
        def fill_colors():
            for i, j in height:
                if (i // 32 + j // 32) % 2 == 0:  # 调整间隔大小以适应粒子的密度
                    colors[i, j] = ti.Vector([0.22, 0.72, 0.52])
                else:
                    colors[i, j] = ti.Vector([1, 0.334, 0.52])

        # 二维转一维
        @ti.kernel
        def flatten_fields():
            for i, j in ti.ndrange(Nx, Ny):
                idx = i * Nx + j
                particles_pos[idx] = ti.Vector([i * dx - 0.5, height[i, j], j * dy - 0.5])
                particles_color[idx] = colors[i, j]

        window = ti.ui.Window('2D  Equation', (800, 800), show_window=True)
        # window = ti.ui.Window('2D  Equation', (800, 800),show_window=False)

        canvas = window.get_canvas()
        canvas.set_background_color((1, 1, 1))
        scene = window.get_scene()

        # 设置摄像机
        camera = ti.ui.make_camera()
        camera.position(-15, 15, 0)
        camera.lookat(2, 0, 2)
        camera.fov(20)

        initialize_wave()
        t = 0
        images = []  # 存储图像帧

        while window.running:
            if t == 100:
                break
            t = t + 1
            update_wave(t)

            fill_colors()
            flatten_fields()  # 更新粒子位置和颜色

            camera.track_user_inputs(window, movement_speed=0.03, hold_key=ti.ui.LMB)
            scene.set_camera(camera)

            # 设置点光源和环境光源
            scene.point_light(pos=(1, 2, 2), color=(0.8, 0.8, 1))  # 调整光源颜色为偏蓝色调
            scene.ambient_light((0.2, 0.2, 0.6))  # 调整环境光为偏蓝色调
            # 使用颜色渲染场景
            scene.particles(particles_pos, radius=0.02, per_vertex_color=particles_color)  # 可以调整粒子半径
            print(particles_pos)
            # 渲染场景
            canvas.scene(scene)
            print("1")
            window.save_image(str(t) + '.png')
            window.show()
        subprocess.run(['python', 'Record_heat.py'], check=True)
    def exe_dim1_solver(self):
        self.init_func()
        self.height_solver_dim1()
        self.save_data_dim1()

    def exe_dim2_solver(self):
        self.init_func()
        self.height_solver_dim2()
        self.save_data_dim2()

@ti.data_oriented
class laplace_equ():
    def __init__(self, len, dim, dw, a, b):
        # ti.reset()  # 清除之前的状态和数据
        self.len = len
        self.dim = dim
        self.dw = dw
        self.a = a
        self.b = b
        # dim1
        self.phi_x = ti.field(ti.f32, shape=int(self.len[0] / self.dw[0]))
        # dim2
        self.phi_xy = ti.field(ti.f32, shape=(int(self.len[0] / self.dw[0]), int(self.len[1] / self.dw[1])))
        # dim3
        self.phi_xyz = ti.field(ti.f32, shape=(
        int(self.len[0] / self.dw[0]), int(self.len[1] / self.dw[1]), int(self.len[2] / self.dw[2])))

    @ti.kernel
    def laplace_solver_dim1(self):
        # 初始化边界条件
        a1 = self.a[0]
        b1 = self.b[0]
        dx = self.dw[0]
        len = self.len[0]
        n = int(len / dx)  # 网格点数量

        # 线性插值初始化内部点
        self.phi_x[0] = a1
        self.phi_x[int(len / dx) - 1] = b1
        for i in range(1, n - 1):
            self.phi_x[i] = a1 + (b1 - a1) * i / (n - 1)

        # 标记是否收敛，这里用一个较大的数开始
        max_diff = 1.0
        while max_diff > 1e-5:  # 收敛条件
            max_diff = 0.0
            for i in range(1, n - 1):
                old_value = self.phi_x[i]
                # 使用拉普拉斯方程的离散近似更新内部点
                self.phi_x[i] = 0.5 * (self.phi_x[i - 1] + self.phi_x[i + 1])
                # 更新最大差异
                diff = abs(self.phi_x[i] - old_value)
                if diff > max_diff:
                    max_diff = diff

    @ti.kernel
    def laplace_solver_dim2(self):
        a1, a2 = self.a[0], self.a[1]  # 沿x和y的边界条件
        b1, b2 = self.b[0], self.b[1]  # 沿x和y的边界条件
        dx = self.dw[1]
        dy = self.dw[2]
        len1, len2 = self.len[0], self.len[1]
        n_x = int(len1 / dx)
        n_y = int(len2 / dy)

        # 边界条件初始化
        for j in ti.ndrange((0, n_y)):  # x方向的边界
            self.phi_xy[0, j] = a1
            self.phi_xy[n_x - 1, j] = b1
        for i in ti.ndrange((0, n_x)):  # y方向的边界
            self.phi_xy[i, 0] = a2
            self.phi_xy[i, n_y - 1] = b2

        # 线性插值初始化内部点
        for i in range(1, n_x - 1):
            for j in range(1, n_y - 1):
                # 插值
                self.phi_xy[i, j] = (a1 * (n_x - 1 - i) + b1 * i) / (n_x - 1) + (a2 * (n_y - 1 - j) + b2 * j) / (
                        n_y - 1)

        # 迭代更新内部点，并检测收敛
        max_diff = 1.0  # 初始设为较大值以进入循环
        while max_diff > 1e-5:  # 收敛阈值
            max_diff = 0.0
            for i in range(1, n_x - 1):
                for j in range(1, n_y - 1):
                    old_value = self.phi_xy[i, j]
                    # 根据拉普拉斯方程的离散近似更新内部点
                    self.phi_xy[i, j] = 0.25 * (
                            self.phi_xy[i + 1, j] + self.phi_xy[i - 1, j] + self.phi_xy[i, j + 1] + self.phi_xy[
                        i, j - 1])
                    # 计算更新后的最大差异
                    diff = abs(self.phi_xy[i, j] - old_value)
                    if diff > max_diff:
                        max_diff = diff

    def print_field_dim1(self):
        for i in range(0, int(self.len[0] / self.dw[0])):
            print(f"x[{i}] = {self.phi_x[i]}")  # 打印field的每个元素

    def print_field_dim2(self):
        for i, j in ti.ndrange((0, int(self.len[0] / self.dw[0])), (0, int(self.len[1] / self.dw[1]))):
            print(f"x[{i}, {j}] = {self.phi_xy[i, j]}")  # 打印field的每个元素

    def draw_dim1(self):
        y = self.phi_x.to_numpy()
        dx = self.dw[0]
        len_x = self.len[0]
        x = np.arange(0, len_x, dx)

        fig = go.Figure(data=go.Scatter(x=x, y=y, mode='lines'))
        fig.update_layout(title='Laplace Equation Solution', xaxis_title='X', yaxis_title='Y', autosize=False,
                          width=800, height=600, margin=dict(l=50, r=50, b=100, t=100))

        # 转换图表为HTML字符串
        plot_div = fig.to_html(full_html=False)

        return plot_div

    def draw_dim2(self):
        Z = self.phi_xy.to_numpy()
        dx = self.dw[0]
        dy = self.dw[1]
        len1 = self.len[0]
        len2 = self.len[1]
        x = np.arange(0, len1, dx)
        y = np.arange(0, len2, dy)
        X, Y = np.meshgrid(y, x)

        # 使用Plotly创建图形
        fig = go.Figure(data=[go.Surface(z=Z, x=X, y=Y)])
        fig.update_layout(title='Laplace Equation Solution', autosize=False, width=800, height=600,
                          margin=dict(l=50, r=50, b=100, t=100))

        # 转换图表为HTML字符串
        plot_div = fig.to_html(full_html=False)
        return plot_div

    def exe_dim1_solver(self):
        self.laplace_solver_dim1()
        self.draw_dim1()

    def exe_dim2_solver(self):
        self.laplace_solver_dim2()
        self.draw_dim2()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/solve_integral', methods=['POST'])
def solve_integral():
    data = request.get_json()  # 获取 JSON 数据
    parameter_integral = data['parameter_integral']  # 从 JSON 数据中获取 'parameter' 键的值
    equation_solver = calculator_normal(parameter_integral, 0)
    solve_integral_solution = equation_solver.solve_integral_exe()
    return jsonify({'solve_integral_solution': solve_integral_solution})
@app.route('/solve_non_equations', methods=['POST'])
def solve_non_equations():
    data = request.get_json()  # 获取 JSON 数据
    parameter_non_equations = data['parameter_non_equations']  # 从 JSON 数据中获取 'parameter' 键的值
    equation_solver = calculator_normal(parameter_non_equations, 0)
    solve_non_equations_solution = equation_solver.solve_non_equations_exe()
    return jsonify({'solve_non_equations_solution': solve_non_equations_solution})
@app.route('/solve_matrix', methods=['POST'])
def solve_matrix():
    data = request.get_json()  # 获取 JSON 数据
    parameter_matrix = data['parameter_matrix']  # 从 JSON 数据中获取 'parameter' 键的值
    equation_solver = calculator_normal(parameter_matrix, 0)
    solve_matrix_solution = equation_solver.calculate_matrix_exe()
    return jsonify({'solve_matrix_solution': solve_matrix_solution})

@app.route('/solve_find_extreme', methods=['POST'])
def find_extreme():
    data = request.get_json()  # 获取 JSON 数据
    parameter_find_extreme = data['parameter_find_extreme']  # 从 JSON 数据中获取 'parameter' 键的值
    equation_solver = calculator_normal(parameter_find_extreme, 0)
    solve_find_extreme_solution = equation_solver.find_extreme_exe()
    return jsonify({'solve_find_extreme_solution': solve_find_extreme_solution})

@app.route('/solve_linear_system', methods=['POST'])
def solve_linear_system():
    data = request.get_json()  # 获取 JSON 数据
    parameter1_linear_system = data['parameter1_linear_system']
    parameter2_linear_system = data['parameter2_linear_system']# 从 JSON 数据中获取 'parameter' 键的值
    equation_solver = calculator_normal(parameter1_linear_system, 0)
    equation_solver.add_string(parameter2_linear_system)
    solve_linear_system_solution = equation_solver.solve_linear_system_exe()
    return jsonify({'solve_linear_system_solution': solve_linear_system_solution})

@app.route('/solve_nonlinear_equation', methods=['POST'])
def solve_nonlinear_equation():
    data = request.get_json()  # 获取 JSON 数据
    parameter_nonlinear_equation = data['parameter_nonlinear_equation']  # 从 JSON 数据中获取 'parameter' 键的值
    equation_solver = calculator_normal(parameter_nonlinear_equation, 0)
    solve_nonlinear_equation_solution = equation_solver.nonlinear_equation_exe()
    return jsonify({'solve_nonlinear_equation_solution': solve_nonlinear_equation_solution})

# @app.route('/plot_from_latex_multiple', methods=['POST'])
# def plot_from_latex_multiple():
#     data = request.get_json()  # 获取 JSON 数据
#     parameter_plot_from_latex_multiple = data['parameter_plot_from_latex_multiple']  # 从 JSON 数据中获取 'parameter' 键的值
#     equation_solver = calculator_normal(parameter_plot_from_latex_multiple, 0)
#     plot_from_latex_multiple_solution = equation_solver.plot_from_latex_multiple_exe()
#     return jsonify({'plot_from_latex_multiple_solution': plot_from_latex_multiple_solution})
@app.route('/wave', methods=['POST'])
def solve():
    con1 = str(request.form['con1'])
    con2 = str(request.form['con2'])
    dim = int(request.form['dim'])
    len_1 = float(request.form['len_1'])
    len_2 = float(request.form['len_2'])
    len_3 = float(request.form['len_3'])
    dw1 = float(request.form['dw1'])
    dw2 = float(request.form['dw2'])
    dw3 = float(request.form['dw3'])
    dw4 = float(request.form['dw4'])
    a1 = float(request.form['a1'])
    a2 = float(request.form['a2'])
    a3 = float(request.form['a3'])
    b1 = float(request.form['b1'])
    b2 = float(request.form['b2'])
    b3 = float(request.form['b3'])
    v = float(request.form['v'])


    wave_solver = wave_equ(con1, con2, [len_1, len_2, len_3], dim, v, [dw1, dw2, dw3, dw4], [a1, a2, a3],
                           [b1, b2, b3], 100)

    if dim == 1:
        wave_solver.load_data_dim1()
        wave_solver.draw_dim1()
    if dim == 2:
        wave_solver.load_data_dim2()
        wave_solver.draw_dim2()
    video_wave = url_for('static', filename='video_wave.mp4')
    # 假设图片保存在static目录
    return jsonify({'video_wave': video_wave})


@app.route('/heat', methods=['POST'], endpoint='new_heat')
def solve():
    con = str(request.form['con'])
    dim = int(request.form['dim'])
    len_1 = float(request.form['len_1'])
    len_2 = float(request.form['len_2'])
    len_3 = float(request.form['len_3'])
    dw1 = float(request.form['dw1'])
    dw2 = float(request.form['dw2'])
    dw3 = float(request.form['dw3'])
    dw4 = float(request.form['dw4'])
    a1 = float(request.form['a1'])
    a2 = float(request.form['a2'])
    a3 = float(request.form['a3'])
    b1 = float(request.form['b1'])
    b2 = float(request.form['b2'])
    b3 = float(request.form['b3'])
    v = float(request.form['v'])


    height_solver = height_equ(con, [len_1, len_2, len_3], dim, v, [dw1, dw2, dw3, dw4], [a1, a2, a3],
                           [b1, b2, b3], 11)

    if dim == 1:
        height_solver.load_data_dim1()
        height_solver.draw_dim1()
    if dim == 2:
        height_solver.load_data_dim2()
        height_solver.draw_dim2()

    video_heat = url_for('static', filename='video_heat.mp4')
    # 假设图片保存在static目录
    return jsonify({'video_heat': video_heat})


@app.route('/laplace', methods=['POST'])
def laplace_solution():
    dim = int(request.form['dim'])
    len_1 = float(request.form['len_1'])
    len_2 = float(request.form['len_2'])
    len_3 = float(request.form['len_3'])
    dw1 = float(request.form['dw1'])
    dw2 = float(request.form['dw2'])
    dw3 = float(request.form['dw3'])
    a1 = float(request.form['a1'])
    a2 = float(request.form['a2'])
    a3 = float(request.form['a3'])
    b1 = float(request.form['b1'])
    b2 = float(request.form['b2'])
    b3 = float(request.form['b3'])

    # 假设这里是你获取计算结果的方式
    laplace_solver = laplace_equ([len_1, len_2, len_3], dim, [dw1, dw2, dw3], [a1, a2, a3], [b1, b2, b3])  # 使用实际参数初始化

    if dim == 1:
        laplace_solver.exe_dim1_solver()
        plot_div = laplace_solver.draw_dim1()
        return jsonify({'plot_div': plot_div})
    elif dim == 2:
        laplace_solver.exe_dim2_solver()
        plot_div = laplace_solver.draw_dim2()
        return jsonify({'plot_div': plot_div})

    # 将结果传递给HTML模板
    # return jsonify({'plot_div': plot_div})  # 将HTML字符串作为JSON响应返回

@app.route('/reset-taichi', methods=['POST'])
def reset_taichi():
    try:
        ti.reset()  # 重置Taichi
        ti.init(arch=ti.gpu)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()  # 获取数据库连接
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE username = %s', (username,))
        user_pass = cursor.fetchone()

        if user_pass and check_password_hash(user_pass[0], password):
            conn.close()  # 关闭数据库连接
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')

        conn.close()
    return render_template('login.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=False)

# 111
import time
import random
import math
import logging
import platform
import numpy as np  # 轨迹计算
from DrissionPage.common import Keys
from DrissionPage.items import ChromiumTab, ChromiumElement
from DrissionPage import ChromiumOptions, Chromium
from utils.logger_config import setup_logging

setup_logging(logging.INFO)
logger = logging.getLogger(__name__)


class BaseAction:
    """
    基础操作类：负责稳健的元素查找、基础点击、输入和重试机制
    """

    def __init__(self, tab: ChromiumTab):
        self.tab = tab
        # 设置全局查找元素等待时间（DP默认10s，这里显式设置一下）
        self.tab.set.timeouts(10)
        # 判断操作系统用于快捷键适配
        self.is_mac = platform.system() == 'Darwin'

    def wait_random(self, min_s=0.5, max_s=1.5):
        """随机等待"""
        time.sleep(random.uniform(min_s, max_s))

    def _resolve_element(self, loc=None, ele=None, timeout=5, desc="元素"):
        """
        核心优化：统一解析 loc 和 ele 的关系
        1. 只有 loc -> 全局查找 tab.ele(loc)
        2. loc + ele -> 相对查找 ele.ele(loc)
        3. 只有 ele -> 直接返回 ele
        """
        target = None
        try:
            # 情况 3: 只有 ele，没有 loc，直接操作该元素
            if ele and not loc:
                target = ele

            # 情况 2: 有 ele 也有 loc，在 ele 下找 loc
            elif ele and loc:
                # 确保父元素存在（虽然传入的是对象，但在重试循环中可能失效，这里主要做查找）
                target = ele.ele(loc, timeout=timeout)

            # 情况 1: 只有 loc，全局找
            elif loc and not ele:
                target = self.tab.ele(loc, timeout=timeout)

            else:
                logger.error(f"[参数错误] {desc} 必须提供 loc 或 ele")
                return None

            # 统一检查元素是否真的找到了
            if target:
                return target
            else:
                logger.debug(f"[查找失败] {desc} 未找到 (loc={loc}, has_parent={bool(ele)})")
                return None

        except Exception as e:
            logger.warning(f"[查找异常] {desc}: {e}")
            return None

    def safe_click(self, loc=None, ele=None, retry=3, timeout=5, desc="元素"):
        """
        稳健点击（机器风格，追求成功率）
        """
        logger.info(f"[-] [Safe] 准备点击 {desc} ...")
        for i in range(retry):
            target = self._resolve_element(loc, ele, timeout, desc)
            if not target:
                self.wait_random(0.5, 1.0)
                continue

            try:
                # 等待可点击
                if target.wait.clickable(timeout=4, raise_err=False):
                    target.click()
                    logger.info(f"[Safe] 点击成功: {desc}")
                    return True

                # 最后一次重试尝试 JS
                if i == retry - 1:
                    logger.warning(f"[Safe] {desc} 常规点击失败，尝试 JS 点击")
                    target.click(by_js=True)
                    return True

            except Exception as e:
                logger.warning(f"[Safe] 点击异常 {desc}: {e}")

            self.wait_random(0.5, 1.0)

        logger.error(f"[Safe] 点击失败: {desc}")
        return False

    def safe_input(self, value, loc=None, ele=None, clear=True, retry=3, timeout=5, desc="输入框"):
        """
        稳健输入（机器风格）
        """
        logger.info(f"[-] [Safe] 准备输入 {desc} -> {value}")
        for i in range(retry):
            target = self._resolve_element(loc, ele, timeout, desc)
            if not target:
                self.wait_random(0.5, 1.0)
                continue

            try:
                if clear:
                    target.clear()
                    self.tab.wait(0.2)

                target.input(value)
                self.tab.wait(0.2)

                # 验证
                if str(target.value) == str(value) or str(target.attr("value")) == str(value):
                    logger.info(f"[Safe] 输入成功: {desc}")
                    return True
            except Exception as e:
                logger.warning(f"[Safe] 输入异常 {desc}: {e}")

            self.wait_random(0.5, 1.0)

        logger.error(f"[Safe] 输入失败: {desc}")
        return False


class HumanAction(BaseAction):
    """
    拟人操作类：继承自 BaseAction，拥有相同的查找逻辑，但行为更像人
    """
    def __init__(self, tab: ChromiumTab):
        super().__init__(tab)
        # 初始化内部记录（作为兜底）
        self.curr_x = 0
        self.curr_y = 0

        # 1. 启动时注入一次 JS 追踪器
        self._ensure_mouse_tracker()

    def _ensure_mouse_tracker(self):
        """
        注入 JS 监听器，用于实时获取鼠标位置
        """
        js_code = """
        if (!window._mouse_tracker_attached) {
            window._mouse_x = 0;
            window._mouse_y = 0;
            window._mouse_tracker_attached = true;

            document.addEventListener('mousemove', function(e) {
                window._mouse_x = e.clientX;
                window._mouse_y = e.clientY;
            });
            console.log('Mouse tracker attached');
        }
        """
        try:
            self.tab.run_js(js_code)
        except Exception:
            pass

    def _get_real_mouse_pos(self):
        """
        从浏览器获取真实的鼠标当前位置
        """
        # 每次获取前，先确保 JS 监听器还在（防止页面刷新后丢失）
        self._ensure_mouse_tracker()

        try:
            # 获取 JS 记录的坐标
            pos = self.tab.run_js("return [window._mouse_x, window._mouse_y];")

            # 如果 JS 返回了有效坐标，且不是默认的 (0,0)（除非真的在0,0）
            # 注意：刚刷新页面没动鼠标时，JS可能是0,0，这时尽量用我们内存记的
            if pos and (pos[0] != 0 or pos[1] != 0):
                self.curr_x, self.curr_y = pos[0], pos[1]
                return self.curr_x, self.curr_y

            # 如果页面刚刷新，JS 还没捕获到移动，就用 Python 记录的兜底
            return self.curr_x, self.curr_y

        except Exception as e:
            logger.warning(f"获取鼠标位置失败: {e}")
            return self.curr_x, self.curr_y

    def _get_bezier_track(self, start_x, start_y, end_x, end_y):
        """生成轨迹点列表"""
        # 随机控制点
        control_x = (start_x + end_x) / 2 + random.choice([1, -1]) * random.randint(50, 150)
        control_y = (start_y + end_y) / 2 + random.choice([1, -1]) * random.randint(50, 150)

        dist = math.hypot(end_x - start_x, end_y - start_y)
        # 距离越近步数越少
        steps = int(dist / random.randint(15, 25)) + 3

        path = []
        for t in np.linspace(0, 1, steps):
            x = (1 - t) ** 2 * start_x + 2 * t * (1 - t) * control_x + t ** 2 * end_x
            y = (1 - t) ** 2 * start_y + 2 * t * (1 - t) * control_y + t ** 2 * end_y
            path.append((int(x), int(y)))
        return path

    def _human_move_to_ele(self, target_ele):
        """
        连续轨迹移动：先获取真实起点，再算轨迹
        """
        rect = target_ele.rect
        if not rect: return

        # --- 核心修改：起点改为实时获取的真实位置 ---
        start_x, start_y = self._get_real_mouse_pos()
        # ---------------------------------------

        # 终点（元素内随机点）
        end_x = rect.location[0] + rect.size[0] * random.uniform(0.2, 0.8)
        end_y = rect.location[1] + rect.size[1] * random.uniform(0.2, 0.8)

        # 生成轨迹
        track = self._get_bezier_track(start_x, start_y, end_x, end_y)

        # 移动
        for i, point in enumerate(track):
            # ... (速度控制代码同上) ...
            if i < len(track) * 0.2 or i > len(track) * 0.8:
                step_dur = random.uniform(0.01, 0.03)
            else:
                step_dur = random.uniform(0.005, 0.01)

            self.tab.actions.move_to(point, duration=step_dur)

        # 移动完更新内存记录
        self.curr_x, self.curr_y = end_x, end_y

        # 修正终点
        self.tab.actions.move_to((end_x, end_y), duration=0.1)

    def _human_scroll_to(self, ele):
        """拟人滚动"""
        if ele.states.is_whole_in_viewport:
            return

        if random.random() > 0.7:
            # 偶尔的反向假动作
            self.tab.scroll.up(random.randint(20, 100))
            self.wait_random(0.1, 0.3)

        self.tab.scroll.to_see(ele, center=True)
        self.wait_random(0.3, 0.7)

    def human_click(self, loc=None, ele=None, retry=3, timeout=5, desc="元素"):
        """
        拟人点击：查找 -> 滚动 -> 轨迹移动 -> 抖动 -> 点击
        """
        logger.info(f"[-] [Human] 准备点击 {desc}")

        for i in range(retry):
            target = self._resolve_element(loc, ele, timeout, desc)
            if not target:
                self.wait_random(1, 2)
                continue

            try:
                # 1. 确保在视口
                if not target.states.is_whole_in_viewport:
                    self.tab.scroll.to_see(target, center=True)
                    self.wait_random(0.5, 0.8)
                    # 滚动会导致鼠标相对位置变化，滚动后强制让 JS 更新一下
                    # 这里的 trick 是：可以稍微微动一下鼠标来触发 JS 监听
                    self.tab.actions.move(1, 1, duration=0.01)

                # --- 步骤 2: 核心检查 - 等待元素可被点击 ---
                # wait.clickable() 会检查：
                # 1. 元素存在且显示
                # 2. 元素未被禁用 (enabled)
                # 3. 元素没有被其他层遮挡 (overlaid)
                # 4. 元素不在运动中 (stopped)
                if not target.wait.clickable(timeout=2, raise_err=False):
                    logger.warning(f"[Human] {desc} 当前不可点击 (被遮挡或加载中)，重试...")
                    # 如果是遮挡，稍微动一下滚动条可能就出来了
                    self.tab.scroll.up(10)
                    self.wait_random(0.5, 1.0)
                    continue

                # --- 步骤 3: 连续轨迹移动 ---
                # 只有确认能点了，才移动鼠标过去，这样更符合逻辑
                self._human_move_to_ele(target)

                # 步骤 4: 悬停 + 手抖
                self.wait_random(0.1, 0.3)
                for _ in range(random.randint(0, 2)):
                    jitter_x = self.curr_x + random.randint(-2, 2)
                    jitter_y = self.curr_y + random.randint(-2, 2)
                    self.tab.actions.move_to((jitter_x, jitter_y), duration=0.05)

                # 5. 物理点击逻辑
                self.tab.actions.hold()
                time.sleep(random.uniform(0.06, 0.15))  # 按下持续时间
                self.tab.actions.release()

                # 6. 点击后微移 (模拟抬手惯性)
                self.curr_x += random.randint(-3, 3)
                self.curr_y += random.randint(-3, 3)
                self.tab.actions.move_to((self.curr_x, self.curr_y), duration=0.1)

                logger.info(f"[Human] 点击成功: {desc}")
                self.wait_random(0.3, 0.8)
                return True

            except Exception as e:
                logger.warning(f"[Human] 点击异常 (第{i + 1}次) {desc}: {e}", exc_info=True)
                self.wait_random(1, 2)

        logger.error(f"[Human] 点击失败: {desc}")
        return False

    def human_type(self, text, loc=None, ele=None, retry=3, timeout=5, desc="输入框"):
        """
        拟人输入：点击 -> 全选删除 -> 模拟打字(含输错回退)
        """
        logger.info(f"[-] [Human] 准备输入 {desc}")

        for i in range(retry):
            # 复用 click 逻辑先激活输入框
            if not self.human_click(loc, ele, retry=1, timeout=timeout, desc=desc):
                continue

            # 重新获取一次元素对象用于发送按键（因为click可能导致DOM微变）
            target = self._resolve_element(loc, ele, timeout, desc)
            if not target:
                self.wait_random(1, 2)
                continue

            try:
                # 1. 模拟全选删除
                ctrl_key = Keys.META if self.is_mac else Keys.CTRL
                self.tab.actions.key_down(ctrl_key)
                self.tab.actions.type('a')
                self.tab.actions.key_up(ctrl_key)
                self.wait_random(0.1, 0.3)
                self.tab.actions.type(Keys.BACKSPACE)
                self.wait_random(0.2, 0.5)

                # 2. 逐字输入
                char_list = list(str(text))
                idx = 0
                while idx < len(char_list):
                    char = char_list[idx]

                    # 模拟输错 (3% 概率)
                    if random.random() < 0.03:
                        wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                        self.tab.actions.type(wrong_char)
                        self.wait_random(0.1, 0.3)
                        self.tab.actions.type(Keys.BACKSPACE)
                        self.wait_random(0.1, 0.3)
                        # 不增加 idx，下次循环重试正确字符
                        continue

                    self.tab.actions.type(char)

                    # 动态打字延迟
                    if char == ' ':
                        time.sleep(random.uniform(0.15, 0.25))
                    else:
                        # 0.05 - 0.2s 波动
                        time.sleep(max(0.02, random.normalvariate(0.1, 0.05)))

                    idx += 1

                logger.info(f"[Human] 输入完成: {desc}")

                # 3. 验证
                self.wait_random(0.5, 1.0)
                # 某些输入框 value 更新有延迟，或者在 shadowDOM 里，这里简单验证
                # 如果不需要强验证，可以注释掉下面这几行，因为拟人输入通常不会“失败”除非焦点丢了
                curr_val = target.value
                if curr_val and str(text) in str(curr_val):
                    logger.info(f"[Human] 输入完成: {desc}")
                    return True
                else:
                    logger.warning(f"[Human] 输入完成(校验输入未通过，重试): {desc}")
                    self.wait_random(1, 2)


            except Exception as e:
                logger.warning(f"[Human] 输入异常 (第{i + 1}次) {desc}: {e}", exc_info=True)
                self.wait_random(1, 2)

        logger.error(f"[Human] 输入失败: {desc}")
        return False


# --- 使用示例 ---
if __name__ == '__main__':
    co = ChromiumOptions()
    # co.set_local_port(9222).set_user_data_path("F:\web3\chrome_profile")
    co.set_local_port(9222).set_user_data_path("/Users/qkb/Desktop/others/MyChromeProfile1")
    browser = Chromium(co)
    tab = browser.latest_tab

    # 实例化 Bot
    bot = HumanAction(tab)

    # 场景 1: 只有 loc (全局查找)
    # bot.human_type("Hello World", loc="#kw", desc="百度搜索框")
    # bot.human_click(loc="#su", desc="百度一下按钮")

    # 场景 2: 只有 ele (已知元素对象)
    # some_ele = tab.ele("#kw")
    # bot.human_type("Direct Element", ele=some_ele)

    # 场景 3: loc + ele (相对查找)
    # parent = tab.ele("#form")
    # bot.human_click(loc="t:input", ele=parent, desc="表单内的输入框")
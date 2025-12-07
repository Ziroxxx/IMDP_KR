import dearpygui.dearpygui as dpg
import os
from config import SimulationParams
from engine import ChattyEngine

class SimulationApp:
    def __init__(self):
        self.engine = None
        self.isRunning = False
        self.frameCounter = 0
        self.stepAccumulator = 0.0
        self.plotDataTime = []
        self.plotDataQueue = []
        dpg.create_context()
        self.setupFont()
        self.createGui()

    def setupFont(self):
        """Кириллица на macOS/Windows/Linux — проверено в 2025 году"""
        with dpg.font_registry():
            # Список возможных путей к шрифтам с кириллицей
            possible_paths = [
                "/System/Library/Fonts/Supplemental/Arial.ttf",           # macOS (основной)
                "/System/Library/Fonts/SFNS.ttf",                         # macOS 14+
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Arial Unicode.ttf",
                "C:/Windows/Fonts/arial.ttf",                             # Windows
                "C:/Windows/Fonts/segoeui.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",        # Linux
                "/usr/share/fonts/TTF/arial.ttf",
            ]

            font_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    font_path = path
                    break

            # Если шрифт не найден — попробуем любой TTF в папке проекта
            if font_path is None:
                local_fonts = ["arial.ttf", "Arial.ttf", "inter.ttf", "Inter-Regular.ttf", "Roboto-Regular.ttf"]
                for local in local_fonts:
                    if os.path.exists(local):
                        font_path = local
                        break

            if font_path is None:
                print("Шрифт с кириллицей не найден — будет без русских букв")
                return

            print(f"Загружаем шрифт: {font_path}")

            # ВАЖНО: сначала создаём шрифт, потом уже к нему привязываем диапазоны
            main_font = dpg.add_font(font_path, 18)

            # Привязываем диапазоны ТОЛЬКО к созданному шрифту
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic, parent=main_font)
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Default, parent=main_font)

            # Применяем глобально
            dpg.bind_font(main_font)

    def createGui(self):
        dpg.create_viewport(title='Симуляция Chatty I/O Antipattern', width=1300, height=900)
        
        with dpg.window(tag="MainWindow", no_title_bar=False, no_resize=False, no_move=False):
            with dpg.group(horizontal=True):

                # === Левая панель управления ===
                with dpg.child_window(width=400, autosize_y=True, border=True):
                    dpg.add_text("Параметры симуляции", color=(0, 255, 255))
                    dpg.add_separator()

                    dpg.add_slider_int(label="Время симуляции (сек)", tag="s_total_time", default_value=3000, min_value=100, max_value=10000)
                    dpg.add_slider_float(label="Скорость симуляции ×", tag="s_speed", default_value=1.0, min_value=0.1, max_value=20.0, format="%.1f")
                    dpg.add_separator()

                    dpg.add_text("Генерация трафика")
                    with dpg.group(horizontal=True):
                        dpg.add_text("Интервал:")
                        dpg.add_drag_int(default_value=3, tag="s_arr_min", width=80, min_value=1, max_value=50)
                        dpg.add_drag_int(default_value=12, tag="s_arr_max", width=80, min_value=1, max_value=100)
                    dpg.add_slider_float(label="Вероятность Chatty-запроса", tag="s_prob", default_value=0.7, min_value=0.0, max_value=1.0)

                    dpg.add_separator()
                    dpg.add_text("Время обработки одного подзапроса")
                    with dpg.group(horizontal=True):
                        dpg.add_drag_int(default_value=4, tag="s_srv_min", width=80)
                        dpg.add_drag_int(default_value=12, tag="s_srv_max", width=80)
                    dpg.add_drag_int(label="Сетевая задержка (мс)", tag="s_latency", default_value=15, min_value=0, max_value=100)

                    dpg.add_separator()
                    dpg.add_text("Архитектура")
                    dpg.add_slider_int(label="Количество серверов", tag="s_servers", default_value=4, min_value=1, max_value=10)
                    dpg.add_slider_int(label="Размер буфера очереди", tag="s_buf", default_value=30, min_value=5, max_value=200)
                    with dpg.group(horizontal=True):
                        dpg.add_text("Подзапросов в Chatty:")
                        dpg.add_drag_int(default_value=5, tag="s_chatty_min", width=80, min_value=2)
                        dpg.add_drag_int(default_value=15, tag="s_chatty_max", width=80, min_value=2)

                    dpg.add_separator()
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="ЗАПУСК", tag="btn_start", callback=self.startSimulation, width=150, height=40)
                        dpg.add_button(label="СТОП", tag="btn_stop", callback=self.stopSimulation, width=150, height=40, show=False)

                    dpg.add_separator()
                    dpg.add_text("Статистика реального времени:", color=(0, 255, 0))
                    dpg.add_text("Ожидание запуска...", tag="txt_stats")

                # === Правая часть: визуализация ===
                with dpg.group():
                    # Один единственный drawlist — только ОДИН раз!
                    with dpg.drawlist(width=850, height=450, tag="canvas_root"):
                        dpg.draw_rectangle((0, 0), (850, 450), fill=(20, 20, 40))

                    # График очереди
                    with dpg.plot(label="Длина очереди I/O (время)", height=380, width=-1):
                        dpg.add_plot_legend()
                        dpg.add_plot_axis(dpg.mvXAxis, label="Время", tag="xaxis")
                        with dpg.plot_axis(dpg.mvYAxis, label="Заявок в очереди"):
                            dpg.add_line_series([], [], label="Очередь", tag="series_queue")

    def getParams(self):
        return SimulationParams(
            totalTime=dpg.get_value('s_total_time'),
            arrivalInterval=(dpg.get_value('s_arr_min'), dpg.get_value('s_arr_max')),
            probChatty=dpg.get_value('s_prob'),
            serviceTime=(dpg.get_value('s_srv_min'), dpg.get_value('s_srv_max')),
            networkLatency=dpg.get_value('s_latency'),
            numServers=dpg.get_value('s_servers'),
            bufferSize=dpg.get_value('s_buf'),
            chattyMin=dpg.get_value('s_chatty_min'),
            chattyMax=dpg.get_value('s_chatty_max')
        )

    def startSimulation(self):
        self.engine = ChattyEngine(self.getParams())
        self.isRunning = True
        self.stepAccumulator = 0.0
        self.plotDataTime = []
        self.plotDataQueue = []
        dpg.hide_item('btn_start')
        dpg.show_item('btn_stop')

    def stopSimulation(self):
        self.isRunning = False
        dpg.hide_item('btn_stop')
        dpg.show_item('btn_start')
        self.updateStats(premature=True)

    def updateStats(self, premature=False):
        if not self.engine: return
        res = self.engine.getResults()
        status = 'ОСТАНОВЛЕНО' if premature else 'РАБОТАЕТ'
        if not self.isRunning and not premature: status = 'ЗАВЕРШЕНО'
        txt = (
            f"Статус: {status} | Время: {self.engine.currentTime}\n"
            f"---------------------------\n"
            f"ВСЕГО ЗАЯВОК: {res['totalReq']}\n"
            f"Обработано: {res['processed']}\n"
            f"Отказано: {res['rejected']} ({res['rejProb']:.1f}%)\n"
            f"Загр. серверов: {res['kAvg']:.1f}%"
        )
        dpg.set_value('txt_stats', txt)

    def drawLoop(self):
        # БОЛЬШЕ НИЧЕГО НЕ ОЧИЩАЕМ — DearPyGui делает это автоматически!
        if not self.engine:
            dpg.draw_text((300, 200), "Нажмите ЗАПУСК", color=(200, 200, 200), parent="canvas_root")
            return

        RED   = (230, 70, 70)
        GREEN = (70, 230, 70)
        YELLOW = (240, 200, 50)
        GRAY  = (150, 150, 150)
        WHITE = (255, 255, 255)

        # Клиент
        dpg.draw_circle((70, 225), 30, fill=YELLOW, parent="canvas_root")
        dpg.draw_text((45, 270), "Client", color=WHITE, size=18, parent="canvas_root")

        # Стрелка к очереди
        dpg.draw_line((100, 225), (200, 225), color=GRAY, thickness=3, parent="canvas_root")
        dpg.draw_arrow((200, 225), (180, 225), color=GRAY, thickness=3, parent="canvas_root")

        # Очередь
        self.drawQueue(220, 180, self.engine.ioQueue, self.engine.params.bufferSize, RED)

        # Стрелки к серверам
        for i in range(min(len(self.engine.servers), 8)):
            y = 100 + i * 55
            dpg.draw_line((400, 225), (500, y), color=GRAY, thickness=2, parent="canvas_root")

        # Серверы
        for i, srv in enumerate(self.engine.servers[:8]):
            y = 80 + i * 55
            color = RED if not srv.isFree else GREEN
            dpg.draw_rectangle((520, y), (680, y+45), fill=color, color=WHITE, parent="canvas_root")
            status = "BUSY" if not srv.isFree else "FREE"
            dpg.draw_text((535, y+12), f"Server {i+1}", color=(0,0,0), size=14, parent="canvas_root")
            dpg.draw_text((535, y+28), status, color=(0,0,0), size=12, parent="canvas_root")

    def drawQueue(self, x, y, queue, cap, color):
        box_w, box_h = 15, 25
        gap = 2
        dpg.draw_text((x, y-20), f'Оч: {len(queue)}/{cap}', size=13, parent='canvas_root')
        for i in range(cap):
            bx = x + i*(box_w + gap)
            filled = i < len(queue)
            fill_col = (150, 150, 150) if filled else (40, 40, 40)
            border = color if filled else (80, 80, 80)
            dpg.draw_rectangle((bx, y), (bx+box_w, y+box_h), fill=fill_col, color=border, parent='canvas_root')

    def run(self):
        dpg.setup_dearpygui()
        dpg.show_viewport()
        while dpg.is_dearpygui_running():
            if self.isRunning and self.engine:
                speed = dpg.get_value('s_speed')
                self.stepAccumulator += speed
                while self.stepAccumulator >= 1.0:
                    active = self.engine.step()
                    self.stepAccumulator -= 1.0
                    if not active:
                        self.stopSimulation()
                        break
                if self.frameCounter % 10 == 0:
                    self.plotDataTime.append(self.engine.currentTime)
                    self.plotDataQueue.append(len(self.engine.ioQueue))
                    if len(self.plotDataTime) > 500:
                        self.plotDataTime.pop(0)
                        self.plotDataQueue.pop(0)
                    dpg.set_value('series_queue', [self.plotDataTime, self.plotDataQueue])
                    dpg.fit_axis_data('xaxis')
                self.updateStats()
                self.frameCounter += 1
            self.drawLoop()
            dpg.render_dearpygui_frame()
        dpg.destroy_context()

def run():
    app = SimulationApp()
    app.run()
import streamlit as st
from PIL import Image
import time
import random
import pandas as pd

# ==================== Конфигурация страницы ====================
st.set_page_config(
    page_title="Симуляция антипаттерна Chatty I/O",
    page_icon="📊",
    layout="wide"
)

topo_img = Image.open("prikol.drawio.png")

st.title("🖥️ Имитационное моделирование антипаттерна Chatty I/O")
st.markdown("Курсовая работа • МГТУ им. Н.Э. Баумана • 2025")

st.markdown("### 🖼️ Топология системы")
col1, col2, col3 = st.columns([1,2,1])  # средняя колонка в 2 раза шире
with col2:
    st.image(topo_img, width=400)

# ==================== Модели ====================
class Params:
    def __init__(self, total_time, arrival_min, arrival_max, prob_chatty, service_min, service_max, latency, servers, buffer_size, chatty_min, chatty_max):
        self.total_time = total_time
        self.arrival_min = arrival_min
        self.arrival_max = arrival_max
        self.prob_chatty = prob_chatty
        self.service_min = service_min
        self.service_max = service_max
        self.latency = latency
        self.servers = servers
        self.buffer_size = buffer_size
        self.chatty_min = chatty_min
        self.chatty_max = chatty_max

class Stats:
    def __init__(self):
        self.generated = 0  # Основные заявки
        self.chatty_count = 0
        self.total_subrequests = 0  # Все подзапросы, включая основные
        self.processed = 0
        self.rejected = 0

class Worker:
    def __init__(self):
        self.remaining = 0
        self.busy_time = 0

    def is_free(self):
        return self.remaining <= 0

    def assign(self, duration):
        self.remaining = duration
        self.busy_time += duration

    def tick(self):
        if self.remaining > 0:
            self.remaining -= 1

class ChattySimulator:
    def __init__(self, params: Params):
        self.p = params
        self.stats = Stats()
        self.time = 0
        self.next_arrival = random.randint(params.arrival_min, params.arrival_max)
        self.queue: List[int] = []
        self.servers = [Worker() for _ in range(params.servers)]

    def step(self):
        if self.time >= self.p.total_time:
            return False

        # Генерация заявки
        if self.time >= self.next_arrival:
            self.stats.generated += 1
            is_chatty = random.random() < self.p.prob_chatty
            if is_chatty:
                self.stats.chatty_count += 1
            subrequests = random.randint(self.p.chatty_min, self.p.chatty_max) if is_chatty else 1
            self.stats.total_subrequests += subrequests

            for _ in range(subrequests):
                if len(self.queue) < self.p.buffer_size:
                    self.queue.append(self.time)
                else:
                    self.stats.rejected += 1
            self.next_arrival = self.time + random.randint(self.p.arrival_min, self.p.arrival_max)

        # Обработка
        for server in self.servers:
            if server.is_free() and self.queue:
                self.queue.pop(0)
                duration = random.randint(self.p.service_min, self.p.service_max) + self.p.latency
                server.assign(duration)
                self.stats.processed += 1
            server.tick()

        self.time += 1
        return True

# ==================== Сайдбар с параметрами ====================
with st.sidebar:
    st.header("⚙️ Параметры симуляции")

    total_time = st.slider("Длительность (сек)", 500, 5000, 2000)
    speed = st.slider("Скорость симуляции ×", 1, 50, 10)

    st.subheader("Трафик")
    col1, col2 = st.columns(2)
    arrival_min = col1.number_input("Интервал min", 1, 50, 3)
    arrival_max = col2.number_input("Интервал max", 1, 100, 12)
    prob_chatty = st.slider("Вероятность Chatty (%)", 0.0, 1.0, 0.7, 0.05)

    st.subheader("Обработка")
    col1, col2 = st.columns(2)
    service_min = col1.number_input("Время подзапроса min", 1, 30, 4)
    service_max = col2.number_input("max", 1, 50, 12)
    chatty_min = col1.number_input("Подзапросов min", 2, 30, 5)
    chatty_max = col2.number_input("max", 2, 50, 15)
    latency = st.number_input("Сетевая задержка (мс)", 0, 100, 15)

    st.subheader("Архитектура")
    servers = st.slider("Количество серверов", 1, 10, 4)
    buffer_size = st.slider("Размер буфера", 5, 200, 30)
    col1, col2 = st.columns(2)

    if st.button("🚀 Запустить симуляцию", type="primary"):
        st.session_state.running = True
        st.session_state.sim = ChattySimulator(Params(
            total_time=total_time,
            arrival_min=arrival_min,
            arrival_max=arrival_max,
            prob_chatty=prob_chatty,
            service_min=service_min,
            service_max=service_max,
            latency=latency,
            servers=servers,
            buffer_size=buffer_size,
            chatty_min=chatty_min,
            chatty_max=chatty_max,
        ))
        st.session_state.queue_history = []
        st.session_state.time_history = []

    if st.button("⏹ Стоп"):
        st.session_state.running = False

# ==================== Основная часть ====================
col1, col2 = st.columns([2, 1])

with col2:
    stats_placeholder = st.container()

with col1:
    viz_placeholder = st.container()
    chart_placeholder = st.container()

# ==================== Симуляция и визуализация ====================
if 'running' not in st.session_state:
    st.session_state.running = False

if st.session_state.running:
    sim = st.session_state.sim
    queue_history = st.session_state.queue_history
    time_history = st.session_state.time_history

    for _ in range(sim.p.total_time - sim.time):
        if not sim.step():
            break
        queue_history.append(len(sim.queue))
        time_history.append(sim.time)

        # Real-time обновление
        if len(queue_history) % speed == 0 or sim.time % 100 == 0:  # Обновляем не каждый шаг, чтобы не тормозить
            # Статистика
            with stats_placeholder.container():
                st.subheader("📊 Статистика (real-time)")
                s = sim.stats
                t = max(sim.time, 1)
                utilization = sum(w.busy_time for w in sim.servers) / (t * sim.p.servers) * 100 if sim.p.servers > 0 else 0
                total_requests = s.total_subrequests
                rej_prob = (s.rejected / max(total_requests, 1)) * 100 if total_requests > 0 else 0

                st.metric("Время", f"{sim.time} / {sim.p.total_time} сек")
                st.metric("Заявок всего (основных)", s.generated)
                st.metric("Chatty заявок", s.chatty_count)
                st.metric("Всего подзапросов", total_requests)
                st.metric("Обработано", s.processed)
                st.metric("Отказано", s.rejected)
                st.metric("Вероятность отказа", f"{rej_prob:.1f}%")
                st.metric("Загрузка серверов", f"{utilization:.1f}%")

            # Визуализация
            with viz_placeholder.container():

                col_q, col_s = st.columns([1, 2])

                with col_q:
                    st.markdown("#### 📬 Очередь I/O")
                    queue_len = len(sim.queue)
                    progress = queue_len / sim.p.buffer_size
                    st.progress(progress)
                    st.write(f"**{queue_len} / {sim.p.buffer_size}** заявок")

                    if progress > 0.8:
                        st.error("Очередь почти переполнена!")
                    elif progress > 0.5:
                        st.warning("Высокая нагрузка")

                with col_s:
                    st.markdown("#### 🖥️ Серверы")
                    cols = st.columns(sim.p.servers)
                    for i, server in enumerate(sim.servers):
                        with cols[i]:
                            color = "#e74c3c" if not server.is_free() else "#2ecc71"
                            status = "ЗАНЯТ" if not server.is_free() else "СВОБОДЕН"
                            st.markdown(f"""
                            <div style="padding:10px; background:{color}; color:white; border-radius:10px; text-align:center;">
                                <strong>Server {i+1}</strong><br>
                                {status}
                            </div>
                            """, unsafe_allow_html=True)

            # График
            with chart_placeholder.container():
                df = pd.DataFrame({'Время': time_history, 'Заполненность очереди': queue_history})
                st.line_chart(df, x='Время', y='Заполненность очереди', height=300)

            st.rerun()  # Перезапуск Streamlit для real-time

        time.sleep(0.001)  # Минимальная пауза, чтобы не перегружать

    st.session_state.running = False
    st.success("Симуляция завершена! График сохранён ниже.")

    # Финальный график остаётся
    with chart_placeholder.container():
        df = pd.DataFrame({'Время': time_history, 'Заполненность очереди': queue_history})
        st.line_chart(df, x='Время', y='Заполненность очереди', height=400)

    # Показываем финальную статистику в том же placeholder, чтобы она не исчезала
    with stats_placeholder.container():
        st.subheader("📊 Статистика (финальная)")
        s = sim.stats
        t = max(sim.time, 1)
        utilization = sum(w.busy_time for w in sim.servers) / (t * sim.p.servers) * 100 if sim.p.servers > 0 else 0
        total_requests = s.total_subrequests
        rej_prob = (s.rejected / max(total_requests, 1)) * 100 if total_requests > 0 else 0

        st.metric("Время", f"{sim.time} / {sim.p.total_time} сек")
        st.metric("Заявок всего (основных)", s.generated)
        st.metric("Chatty заявок", s.chatty_count)
        st.metric("Всего подзапросов", total_requests)
        st.metric("Обработано", s.processed)
        st.metric("Отказано", s.rejected)
        st.metric("Вероятность отказа", f"{rej_prob:.1f}%")
        st.metric("Загрузка серверов", f"{utilization:.1f}%")
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image


class PieChart(Image):
    def draw(self, data, dpi=120, size_px=320):
        total = sum([v for _, v, _ in data])
        fig, ax = plt.subplots(figsize=(size_px / dpi, size_px / dpi), dpi=dpi)
        fig.patch.set_alpha(0)

        if total <= 0 or len(data) == 0:
            sizes = [1]
            colors = ['#DDDDDD']
            ax.pie(
                sizes,
                colors=colors,
                startangle=90,
                counterclock=False,
                wedgeprops={'linewidth': 0},
            )
            ax.set(aspect="equal")
            ax.text(0, 0, "Нет\nдоходов", ha='center', va='center', fontsize=14)
        else:
            labels = []
            sizes = []
            colors = []
            for lbl, val, hexc in data:
                if val > 0:
                    labels.append(lbl)
                    sizes.append(val)
                    colors.append(hexc if hexc else '#1F1F1F')

            def autopct(pct):
                return ('{:.1f}%'.format(pct)) if pct > 0.5 else ''

            wedges, _, autotexts = ax.pie(
                sizes,
                labels=None,
                colors=colors,
                startangle=90,
                counterclock=False,
                autopct=autopct,
                pctdistance=0.75,
                wedgeprops={'linewidth': 0},
            )
            ax.set(aspect="equal")

            legend_labels = [f"{labels[i]} — {sizes[i] / 100:.2f}₽" for i in range(len(labels))]
            ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8)

            for text in autotexts:
                text.set_fontsize(9)
                text.set_color('white')
                text.set_weight('bold')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        self.texture = CoreImage(buf, ext='png').texture


class PieAnimatedChart(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress = 0
        self.fps = 1 / 120
        self.speed = 0.1
        self.values = []
        self.colors = []
        self.labels = []
        self._anim_event = None

    def start(self, values, colors, labels):
        self.values = values
        self.colors = colors
        self.labels = labels

        self.progress = 0
        if self._anim_event:
            self._anim_event.cancel()

        self._anim_event = Clock.schedule_interval(self._update, self.fps)

    def _update(self, dt):
        if self.progress >= 1:
            self.progress = 1
            self._draw(self.progress)
            return False

        self._draw(self.progress)
        self.progress += self.speed

    def _draw(self, progress):
        if not self.values:
            return

        fig, ax = plt.subplots(figsize=(3.2, 3.2), dpi=100)
        fig.patch.set_alpha(0)

        total = sum(self.values)
        if total == 0:
            plt.close(fig)
            return

        scaled = [(value / total) * progress for value in self.values]
        safe_scaled = [max(value, 0.0001) for value in scaled]

        remainder = max(0, 1 - progress)
        sizes = safe_scaled + [remainder]
        colors = list(self.colors) + [(0, 0, 0, 0)]
        labels = list(self.labels) + [""]

        wedges, _ = ax.pie(
            sizes,
            colors=colors,
            startangle=90,
            counterclock=False,
            labels=None,
            wedgeprops={'linewidth': 0},
        )

        for index, wedge in enumerate(wedges[:-1]):
            theta_mid = (wedge.theta1 + wedge.theta2) / 2
            angle = np.deg2rad(theta_mid)

            radius = 0.65
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)

            ax.text(
                x,
                y + 0.07,
                labels[index],
                ha='center',
                va='center',
                fontsize=9,
                color='white',
                weight='bold',
                path_effects=[pe.withStroke(linewidth=1, foreground="black")],
            )

            pct = f"{100 * self.values[index] / total:.1f}%"
            ax.text(
                x,
                y - 0.08,
                pct,
                ha='center',
                va='center',
                fontsize=10,
                color='white',
                weight='bold',
                path_effects=[pe.withStroke(linewidth=1, foreground="black")],
            )

        ax.set(aspect='equal')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
        plt.close(fig)

        buf.seek(0)
        self.texture = CoreImage(buf, ext='png').texture

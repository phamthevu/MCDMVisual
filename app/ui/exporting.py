"""Export the visible PlotWidget scene, including native draggable QGraphicsItems."""
from PySide6.QtCore import QRect, QRectF, QSize
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtSvg import QSvgGenerator


def export_plot_widget(plot, path, *, vector=False, width=2400):
    viewport=plot.viewport()
    source=plot.mapToScene(viewport.rect()).boundingRect()
    if source.width()<=0 or source.height()<=0:
        raise ValueError("The chart has no visible area to export.")
    height=max(1,int(width*source.height()/source.width()))
    target=QRectF(0,0,width,height)
    if vector:
        generator=QSvgGenerator();generator.setFileName(str(path));generator.setSize(QSize(width,height));generator.setViewBox(QRect(0,0,width,height));generator.setTitle("MCDMVisualStudio chart")
        painter=QPainter(generator)
        if not painter.isActive():raise OSError("Could not create the SVG output.")
        painter.fillRect(target,QColor("white"));plot.scene().render(painter,target,source);painter.end()
        return
    image=QImage(width,height,QImage.Format.Format_ARGB32_Premultiplied);image.fill(QColor("white"))
    painter=QPainter(image);plot.scene().render(painter,target,source);painter.end()
    if not image.save(str(path),"PNG"):raise OSError("Could not create the PNG output.")

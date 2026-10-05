"""Servicios de dominio (procesamiento de imágenes, generación de PDF)."""
from .image_processing import ImageProcessingError, ImageProcessor, ProcessedImage
from .pdf_generator import PdfReportGenerator, ReportFilters, ReportItem

__all__ = [
    "ImageProcessingError",
    "ImageProcessor",
    "ProcessedImage",
    "PdfReportGenerator",
    "ReportFilters",
    "ReportItem",
]

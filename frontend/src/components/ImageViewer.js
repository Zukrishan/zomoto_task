import { X, Download, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';
import { useState } from 'react';
import { Button } from './ui/button';

export default function ImageViewer({ open, onClose, imageUrl, filename }) {
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);

  if (!open) return null;

  const handleZoomIn = () => setScale(prev => Math.min(prev + 0.25, 3));
  const handleZoomOut = () => setScale(prev => Math.max(prev - 0.25, 0.5));
  const handleRotate = () => setRotation(prev => (prev + 90) % 360);
  const handleDownload = () => window.open(imageUrl, '_blank');

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90" data-testid="image-viewer">
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 z-10 p-2 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
        data-testid="close-image-viewer"
      >
        <X className="h-6 w-6 text-white" />
      </button>

      {/* Controls */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-full px-4 py-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={handleZoomOut}
          className="h-10 w-10 text-white hover:bg-white/20"
          data-testid="zoom-out-btn"
        >
          <ZoomOut className="h-5 w-5" />
        </Button>
        <span className="text-white text-sm min-w-[60px] text-center">{Math.round(scale * 100)}%</span>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleZoomIn}
          className="h-10 w-10 text-white hover:bg-white/20"
          data-testid="zoom-in-btn"
        >
          <ZoomIn className="h-5 w-5" />
        </Button>
        <div className="w-px h-6 bg-white/30 mx-2" />
        <Button
          variant="ghost"
          size="icon"
          onClick={handleRotate}
          className="h-10 w-10 text-white hover:bg-white/20"
          data-testid="rotate-btn"
        >
          <RotateCw className="h-5 w-5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleDownload}
          className="h-10 w-10 text-white hover:bg-white/20"
          data-testid="download-btn"
        >
          <Download className="h-5 w-5" />
        </Button>
      </div>

      {/* Filename */}
      <div className="absolute top-4 left-4 text-white text-sm bg-black/50 px-3 py-1 rounded-full">
        {filename}
      </div>

      {/* Image */}
      <div 
        className="w-full h-full flex items-center justify-center p-8 overflow-hidden"
        onClick={onClose}
      >
        <img
          src={imageUrl}
          alt={filename}
          className="max-w-full max-h-full object-contain transition-transform duration-200"
          style={{
            transform: `scale(${scale}) rotate(${rotation}deg)`,
          }}
          onClick={(e) => e.stopPropagation()}
          data-testid="viewer-image"
        />
      </div>
    </div>
  );
}

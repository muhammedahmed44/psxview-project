import { useEffect, useRef } from 'react'
import Chart from 'chart.js/auto'

interface Props {
  growthAxis: number[]
  upsideCurve: number[]
  impliedGrowthPct: number | null
}

// Line = upside % at each growth rate. Above 0 = price is below fair value.
export default function ValuationChart({ growthAxis, upsideCurve, impliedGrowthPct }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<Chart | null>(null)

  useEffect(() => {
    if (!canvasRef.current) return
    chartRef.current?.destroy() // always destroy the old chart before drawing a new one
    chartRef.current = new Chart(canvasRef.current, {
      type: 'line',
      data: {
        labels: growthAxis.map((g) => `${g}%`),
        datasets: [
          {
            label: 'Upside vs current price',
            data: upsideCurve,
            borderColor: '#2457d6',
            backgroundColor: 'rgba(36,87,214,0.08)',
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2.5,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (i) => `FCF growth ${i[0].label}`,
              label: (i) => ` ${Number(i.raw) >= 0 ? '+' : ''}${Number(i.raw).toFixed(1)}% vs price`,
            },
          },
        },
        scales: {
          x: { grid: { color: '#e3e8f1' }, ticks: { color: '#5d6b82' } },
          y: { grid: { color: '#e3e8f1' }, ticks: { color: '#5d6b82', callback: (v) => `${v}%` } },
        },
      },
      plugins: [
        {
          id: 'marks',
          afterDraw(ch) {
            const { ctx, chartArea: a, scales } = ch
            ctx.save()
            const y0 = scales.y.getPixelForValue(0)
            if (y0 >= a.top && y0 <= a.bottom) {
              ctx.setLineDash([4, 3])
              ctx.strokeStyle = '#9aa7bd'
              ctx.beginPath()
              ctx.moveTo(a.left, y0)
              ctx.lineTo(a.right, y0)
              ctx.stroke()
            }
            if (impliedGrowthPct !== null) {
              const idx = Math.max(0, Math.min(Math.round(impliedGrowthPct / 2), growthAxis.length - 1))
              const x = scales.x.getPixelForValue(idx)
              ctx.setLineDash([])
              ctx.strokeStyle = '#c9302c'
              ctx.lineWidth = 1.5
              ctx.beginPath()
              ctx.moveTo(x, a.top)
              ctx.lineTo(x, a.bottom)
              ctx.stroke()
            }
            ctx.restore()
          },
        },
      ],
    })
    return () => {
      chartRef.current?.destroy()
      chartRef.current = null
    }
  }, [growthAxis, upsideCurve, impliedGrowthPct])

  return (
    <div className="v-chart">
      <canvas ref={canvasRef} />
    </div>
  )
}
'use client'

import React from 'react'
import { motion } from 'framer-motion'

interface TemplateCardProps {
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  title: string
  description: string
  index: number
  onClick: () => void
}

export function TemplateCard({
  icon: Icon,
  title,
  description,
  index,
  onClick,
}: TemplateCardProps) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: 0.18 + index * 0.06 }}
      whileHover={{
        scale: 1.02,
        transition: { duration: 0.2 },
      }}
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      className="group relative overflow-hidden rounded-[18px] p-4 text-left transition-all duration-300 w-full"
      style={{
        background: 'rgba(15,23,42,0.6)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(148,163,184,0.15)',
        boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
      }}
    >
      {/* Hover Glow */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
        style={{
          background:
            'linear-gradient(135deg, rgba(59,130,246,0.05) 0%, transparent 100%)',
          border: '1px solid rgba(59,130,246,0.3)',
          borderRadius: '18px',
        }}
      />

      {/* Accent Glow */}
      <div
        className="absolute -top-10 -left-10 w-20 h-20 rounded-full opacity-0 group-hover:opacity-30 transition-opacity duration-300"
        style={{
          background:
            'radial-gradient(circle, rgba(59,130,246,0.6) 0%, transparent 70%)',
          filter: 'blur(20px)',
        }}
      />

      <div className="relative flex items-start gap-3">
        <div className="relative flex-shrink-0 mt-0.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/10 to-blue-600/5 flex items-center justify-center group-hover:from-blue-500/20 group-hover:to-blue-600/10 transition-all duration-300">
            <Icon className="w-5 h-5 text-blue-400 group-hover:text-blue-300 transition-colors duration-300" />
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="text-white font-medium text-[15px] mb-1 group-hover:text-blue-50 transition-colors duration-300">
            {title}
          </h3>
          <p className="text-slate-400 text-[13px] leading-relaxed line-clamp-2">
            {description}
          </p>
        </div>
      </div>
    </motion.button>
  )
}

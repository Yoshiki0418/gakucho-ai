'use client'

import React from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'

type QRCodeDisplayProps = {
    url: string | null
    onClose?: () => void
}

export const QRCodeDisplay: React.FC<QRCodeDisplayProps> = ({ url, onClose }) => {
    return (
        <AnimatePresence>
            {url && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.3 }}
                    style={{
                        position: 'absolute',
                        top: 16,
                        left: 16,
                        padding: 16,
                        backgroundColor: 'rgba(15, 23, 42, 0.85)',
                        backdropFilter: 'blur(8px)',
                        borderRadius: 16,
                        border: '1px solid rgba(148, 163, 184, 0.2)',
                        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.3)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: 12,
                        zIndex: 10,
                        maxWidth: 200,
                    }}
                >
                    {onClose && (
                        <button
                            onClick={onClose}
                            style={{
                                position: 'absolute',
                                top: 8,
                                right: 8,
                                background: 'none',
                                border: 'none',
                                color: '#94a3b8',
                                cursor: 'pointer',
                                padding: 4,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                borderRadius: '50%',
                                transition: 'background-color 0.2s, color 0.2s',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)'
                                e.currentTarget.style.color = '#e2e8f0'
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.backgroundColor = 'transparent'
                                e.currentTarget.style.color = '#94a3b8'
                            }}
                            aria-label="閉じる"
                        >
                            <X size={16} />
                        </button>
                    )}

                    <div
                        style={{
                            padding: 8,
                            backgroundColor: '#ffffff',
                            borderRadius: 8,
                        }}
                    >
                        <QRCodeSVG value={url} size={140} level="M" includeMargin={false} />
                    </div>

                    <div style={{ textAlign: 'center' }}>
                        <p
                            style={{
                                fontSize: 12,
                                color: '#e2e8f0',
                                margin: 0,
                                fontWeight: 600,
                                letterSpacing: '0.05em',
                            }}
                        >
                            スキャンしてアクセス
                        </p>
                        <p
                            style={{
                                fontSize: 10,
                                color: '#94a3b8',
                                margin: '4px 0 0',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                maxWidth: 160,
                            }}
                            title={url}
                        >
                            {url}
                        </p>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    )
}

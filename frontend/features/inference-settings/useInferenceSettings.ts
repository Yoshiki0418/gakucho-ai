'use client'

import { useCallback, useEffect, useState } from 'react'
import { defaultDraft, EMPTY_DRAFT, parseCatalog, type InferenceDraft, type SettingsCatalog } from './settings'

export function useInferenceSettings() {
  const [catalog, setCatalog] = useState<SettingsCatalog | null>(null)
  const [draft, setDraft] = useState<InferenceDraft>(EMPTY_DRAFT)
  const [mainModel, setMainModel] = useState('')
  const [fillerModel, setFillerModel] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setIsLoading(true)
    setError(null)
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || ''
    fetch(`${apiBase}/api/text-chat/settings`, { signal: controller.signal, cache: 'no-store' })
      .then(async (response) => {
        if (!response.ok) throw new Error('設定一覧を読み込めませんでした。')
        return parseCatalog(await response.json())
      })
      .then((loaded) => {
        if (controller.signal.aborted) return
        setCatalog(loaded)
        setDraft(defaultDraft(loaded))
        setMainModel(loaded.defaults.llm_model)
        setFillerModel(loaded.defaults.filler_model)
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : '設定一覧を読み込めませんでした。')
        }
      })
      .finally(() => { if (!controller.signal.aborted) setIsLoading(false) })
    return () => controller.abort()
  }, [revision])

  const changeDraft = useCallback((key: keyof InferenceDraft, value: string) => {
    setDraft((previous) => ({ ...previous, [key]: value }))
  }, [])

  const changeMainModel = useCallback((model: string) => {
    setMainModel(model)
    if (!catalog?.llm_models.find((candidate) => candidate.id === model)?.supports_temperature) {
      setDraft((previous) => ({ ...previous, temperature: '' }))
    }
  }, [catalog])

  return { catalog, draft, changeDraft, mainModel, changeMainModel, fillerModel, setFillerModel,
    isLoading, error, reload: () => setRevision((previous) => previous + 1) }
}

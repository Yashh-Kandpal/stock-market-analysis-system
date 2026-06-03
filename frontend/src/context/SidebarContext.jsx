import { createContext, useContext, useState, useEffect } from 'react'

const SidebarContext = createContext(null)

export function SidebarProvider({ children }) {
  const [expanded, setExpanded] = useState(() => {
    const saved = localStorage.getItem('stockin_sidebar')
    return saved !== null ? saved === 'true' : true
  })

  useEffect(() => {
    localStorage.setItem('stockin_sidebar', String(expanded))
  }, [expanded])

  const toggle = () => setExpanded(e => !e)

  return (
    <SidebarContext.Provider value={{ expanded, toggle }}>
      {children}
    </SidebarContext.Provider>
  )
}

export const useSidebar = () => {
  const ctx = useContext(SidebarContext)
  if (!ctx) throw new Error('useSidebar must be used within SidebarProvider')
  return ctx
}

"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Input } from "@/components/ui/input"
import { Search } from "lucide-react"

export function SearchBar() {
  const [query, setQuery] = useState("")
  const router = useRouter()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`)
    }
  }

  return (
    <form onSubmit={handleSearch} className="max-w-3xl mx-auto">
      <div className="relative">
        <Search className="absolute left-6 top-1/2 transform -translate-y-1/2 text-muted-foreground h-6 w-6" />
        <Input
          type="search"
          placeholder="Search for videos, categories, or keywords..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-16 h-16 text-xl border-2 focus:border-primary rounded-2xl shadow-lg"
        />
      </div>
    </form>
  )
}

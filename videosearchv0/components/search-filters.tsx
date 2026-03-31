// "use client"

// import { useState } from "react"
// import { Button } from "@/components/ui/button"
// import { Label } from "@/components/ui/label"
// import { Checkbox } from "@/components/ui/checkbox"
// import { Slider } from "@/components/ui/slider"
// import { Badge } from "@/components/ui/badge"
// import { X, RotateCcw, ChevronDown, ChevronRight } from "lucide-react"
// import { Separator } from "@/components/ui/separator"
// import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

// interface Filters {
//   categories: string[]
//   duration: string
//   qualities: string[]
//   licenses: string[]
//   dateRange: string
//   tags: string[]
// }

// interface SearchFiltersProps {
//   filters: Filters
//   onFiltersChange: (filters: Filters) => void
// }

// const categories = ["Lifestyle", "Business", "Travel", "Food & Drink", "Technology", "Music", "Sports", "Education"]

// const qualities = ["HD", "4K", "8K", "Standard"]
// const licenses = ["Standard", "Extended", "Editorial", "Royalty Free"]
// const popularTags = [
//   "Nature",
//   "Urban",
//   "People",
//   "Abstract",
//   "Slow Motion",
//   "Time Lapse",
//   "Aerial",
//   "Close Up",
//   "Vintage",
//   "Modern",
// ]

// export function SearchFilters({ filters, onFiltersChange }: SearchFiltersProps) {
//   const [durationRange, setDurationRange] = useState([0, 300]) // 0-5 minutes
//   const [expandedSections, setExpandedSections] = useState({
//     categories: false,
//     duration: false,
//     quality: false,
//     license: false,
//     tags: false,
//     dateRange: false,
//   })

//   const toggleSection = (section: keyof typeof expandedSections) => {
//     setExpandedSections((prev) => ({
//       ...prev,
//       [section]: !prev[section],
//     }))
//   }

//   const updateFilters = (key: keyof Filters, value: any) => {
//     onFiltersChange({ ...filters, [key]: value })
//   }

//   const toggleArrayFilter = (key: "categories" | "qualities" | "licenses" | "tags", value: string) => {
//     const currentArray = filters[key]
//     const newArray = currentArray.includes(value)
//       ? currentArray.filter((item) => item !== value)
//       : [...currentArray, value]
//     updateFilters(key, newArray)
//   }

//   const toggleTag = (tag: string) => {
//     toggleArrayFilter("tags", tag)
//   }

//   const clearAllFilters = () => {
//     onFiltersChange({
//       categories: [],
//       duration: "",
//       qualities: [],
//       licenses: [],
//       dateRange: "",
//       tags: [],
//     })
//     setDurationRange([0, 300])
//   }

//   const hasActiveFilters = Object.values(filters).some((value) =>
//     Array.isArray(value) ? value.length > 0 : value !== "",
//   )

//   const getFilterCount = (filterKey: keyof Filters) => {
//     const value = filters[filterKey]
//     if (Array.isArray(value)) {
//       return value.length
//     }
//     return value ? 1 : 0
//   }

//   return (
//     <div className="space-y-4">
//       <div className="flex items-center justify-between">
//         <h3 className="text-lg font-semibold">Filters</h3>
//         {hasActiveFilters && (
//           <Button
//             variant="ghost"
//             size="sm"
//             onClick={clearAllFilters}
//             className="text-muted-foreground hover:text-foreground"
//           >
//             <RotateCcw className="h-4 w-4 mr-1" />
//             Clear All
//           </Button>
//         )}
//       </div>

//       {/* Category Filter */}
//       <Collapsible open={expandedSections.categories} onOpenChange={() => toggleSection("categories")}>
//         <CollapsibleTrigger asChild>
//           <Button variant="ghost" className="w-full justify-between p-0 h-auto font-medium">
//             <div className="flex items-center space-x-2">
//               <span className="text-sm">Categories</span>
//               {getFilterCount("categories") > 0 && (
//                 <Badge variant="secondary" className="h-5 px-2 text-xs">
//                   {getFilterCount("categories")}
//                 </Badge>
//               )}
//             </div>
//             {expandedSections.categories ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
//           </Button>
//         </CollapsibleTrigger>
//         <CollapsibleContent className="space-y-2 mt-3">
//           {categories.map((category) => (
//             <div key={category} className="flex items-center space-x-2">
//               <Checkbox
//                 id={category}
//                 checked={filters.categories.includes(category.toLowerCase())}
//                 onCheckedChange={() => toggleArrayFilter("categories", category.toLowerCase())}
//               />
//               <Label htmlFor={category} className="text-sm cursor-pointer">
//                 {category}
//               </Label>
//             </div>
//           ))}
//         </CollapsibleContent>
//       </Collapsible>

//       <Separator />

//       {/* Duration Filter */}
//       <Collapsible open={expandedSections.duration} onOpenChange={() => toggleSection("duration")}>
//         <CollapsibleTrigger asChild>
//           <Button variant="ghost" className="w-full justify-between p-0 h-auto font-medium">
//             <div className="flex items-center space-x-2">
//               <span className="text-sm">Duration</span>
//             </div>
//             {expandedSections.duration ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
//           </Button>
//         </CollapsibleTrigger>
//         <CollapsibleContent className="space-y-3 mt-3">
//           <div className="px-2">
//             <Slider
//               value={durationRange}
//               onValueChange={setDurationRange}
//               max={300}
//               min={0}
//               step={10}
//               className="w-full"
//             />
//             <div className="flex justify-between text-xs text-muted-foreground mt-1">
//               <span>{durationRange[0]}s</span>
//               <span>{durationRange[1]}s</span>
//             </div>
//           </div>
//         </CollapsibleContent>
//       </Collapsible>

//       <Separator />

//       {/* Quality Filter */}
//       <Collapsible open={expandedSections.quality} onOpenChange={() => toggleSection("quality")}>
//         <CollapsibleTrigger asChild>
//           <Button variant="ghost" className="w-full justify-between p-0 h-auto font-medium">
//             <div className="flex items-center space-x-2">
//               <span className="text-sm">Quality</span>
//               {getFilterCount("qualities") > 0 && (
//                 <Badge variant="secondary" className="h-5 px-2 text-xs">
//                   {getFilterCount("qualities")}
//                 </Badge>
//               )}
//             </div>
//             {expandedSections.quality ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
//           </Button>
//         </CollapsibleTrigger>
//         <CollapsibleContent className="space-y-2 mt-3">
//           {qualities.map((quality) => (
//             <div key={quality} className="flex items-center space-x-2">
//               <Checkbox
//                 id={quality}
//                 checked={filters.qualities.includes(quality.toLowerCase())}
//                 onCheckedChange={() => toggleArrayFilter("qualities", quality.toLowerCase())}
//               />
//               <Label htmlFor={quality} className="text-sm cursor-pointer">
//                 {quality}
//               </Label>
//             </div>
//           ))}
//         </CollapsibleContent>
//       </Collapsible>

//       <Separator />

//       {/* License Filter */}
//       <Collapsible open={expandedSections.license} onOpenChange={() => toggleSection("license")}>
//         <CollapsibleTrigger asChild>
//           <Button variant="ghost" className="w-full justify-between p-0 h-auto font-medium">
//             <div className="flex items-center space-x-2">
//               <span className="text-sm">License Type</span>
//               {getFilterCount("licenses") > 0 && (
//                 <Badge variant="secondary" className="h-5 px-2 text-xs">
//                   {getFilterCount("licenses")}
//                 </Badge>
//               )}
//             </div>
//             {expandedSections.license ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
//           </Button>
//         </CollapsibleTrigger>
//         <CollapsibleContent className="space-y-2 mt-3">
//           {licenses.map((license) => (
//             <div key={license} className="flex items-center space-x-2">
//               <Checkbox
//                 id={license}
//                 checked={filters.licenses.includes(license.toLowerCase().replace(" ", "-"))}
//                 onCheckedChange={() => toggleArrayFilter("licenses", license.toLowerCase().replace(" ", "-"))}
//               />
//               <Label htmlFor={license} className="text-sm cursor-pointer">
//                 {license}
//               </Label>
//             </div>
//           ))}
//         </CollapsibleContent>
//       </Collapsible>

//       <Separator />

//       {/* Tags Filter */}
//       <Collapsible open={expandedSections.tags} onOpenChange={() => toggleSection("tags")}>
//         <CollapsibleTrigger asChild>
//           <Button variant="ghost" className="w-full justify-between p-0 h-auto font-medium">
//             <div className="flex items-center space-x-2">
//               <span className="text-sm">Tags</span>
//               {getFilterCount("tags") > 0 && (
//                 <Badge variant="secondary" className="h-5 px-2 text-xs">
//                   {getFilterCount("tags")}
//                 </Badge>
//               )}
//             </div>
//             {expandedSections.tags ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
//           </Button>
//         </CollapsibleTrigger>
//         <CollapsibleContent className="space-y-3 mt-3">
//           <div className="flex flex-wrap gap-2">
//             {popularTags.map((tag) => (
//               <Badge
//                 key={tag}
//                 variant={filters.tags.includes(tag) ? "default" : "outline"}
//                 className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
//                 onClick={() => toggleTag(tag)}
//               >
//                 {tag}
//                 {filters.tags.includes(tag) && <X className="h-3 w-3 ml-1" />}
//               </Badge>
//             ))}
//           </div>
//         </CollapsibleContent>
//       </Collapsible>

//       <Separator />

//       {/* Date Range Filter */}
//       <Collapsible open={expandedSections.dateRange} onOpenChange={() => toggleSection("dateRange")}>
//         <CollapsibleTrigger asChild>
//           <Button variant="ghost" className="w-full justify-between p-0 h-auto font-medium">
//             <div className="flex items-center space-x-2">
//               <span className="text-sm">Upload Date</span>
//               {getFilterCount("dateRange") > 0 && (
//                 <Badge variant="secondary" className="h-5 px-2 text-xs">
//                   1
//                 </Badge>
//               )}
//             </div>
//             {expandedSections.dateRange ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
//           </Button>
//         </CollapsibleTrigger>
//         <CollapsibleContent className="space-y-2 mt-3">
//           {["", "today", "week", "month", "year"].map((range, index) => (
//             <div key={range} className="flex items-center space-x-2">
//               <Checkbox
//                 id={range || "any-date"}
//                 checked={filters.dateRange === range}
//                 onCheckedChange={() => updateFilters("dateRange", range)}
//               />
//               <Label htmlFor={range || "any-date"} className="text-sm cursor-pointer">
//                 {index === 0
//                   ? "Any Time"
//                   : range === "today"
//                     ? "Today"
//                     : range === "week"
//                       ? "This Week"
//                       : range === "month"
//                         ? "This Month"
//                         : "This Year"}
//               </Label>
//             </div>
//           ))}
//         </CollapsibleContent>
//       </Collapsible>
//     </div>
//   )
// }

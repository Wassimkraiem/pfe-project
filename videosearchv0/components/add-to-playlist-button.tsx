'use client'

import { FormEvent, useEffect, useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
	addVideosToPlaylist,
	createPlaylist,
	getPlaylists,
	type PlaylistSummary,
} from '@/lib/playlists-api'

const NEW_PLAYLIST_VALUE = '__new_playlist__'

interface AddToPlaylistButtonProps {
	videoId: string
	videoTitle?: string
	className?: string
	variant?: 'default' | 'secondary' | 'outline' | 'ghost' | 'link'
	size?: 'default' | 'sm' | 'lg' | 'icon'
}

export function AddToPlaylistButton({
	videoId,
	videoTitle,
	className,
	variant = 'outline',
	size = 'sm',
}: AddToPlaylistButtonProps) {
	const { isLoaded, isSignedIn, getToken } = useAuth()
	const [open, setOpen] = useState(false)
	const [loadingPlaylists, setLoadingPlaylists] = useState(false)
	const [playlists, setPlaylists] = useState<PlaylistSummary[]>([])
	const [targetPlaylist, setTargetPlaylist] = useState(NEW_PLAYLIST_VALUE)
	const [newTitle, setNewTitle] = useState('')
	const [newDescription, setNewDescription] = useState('')
	const [submitting, setSubmitting] = useState(false)
	const [errorMessage, setErrorMessage] = useState<string | null>(null)
	const [successMessage, setSuccessMessage] = useState<string | null>(null)

	useEffect(() => {
		if (!open || !isSignedIn) return

		let cancelled = false
		const loadPlaylists = async () => {
			setLoadingPlaylists(true)
			setErrorMessage(null)
			try {
				const token = await getToken()
				if (!token) {
					setErrorMessage('Session expired. Please sign in again.')
					return
				}
				const items = await getPlaylists(token)
				if (!cancelled) {
					setPlaylists(items)
					if (items.length > 0) {
						setTargetPlaylist(items[0].id.toString())
					}
				}
			} catch (error) {
				if (!cancelled) {
					console.error('Failed to load playlists', error)
					setErrorMessage('Could not load playlists.')
				}
			} finally {
				if (!cancelled) setLoadingPlaylists(false)
			}
		}

		loadPlaylists()
		return () => {
			cancelled = true
		}
	}, [open, isSignedIn, getToken])

	const openDialog = () => {
		if (!isLoaded || !isSignedIn) return
		setErrorMessage(null)
		setSuccessMessage(null)
		setOpen(true)
	}

	if (!isLoaded || !isSignedIn) return null

	const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
		event.preventDefault()
		setSubmitting(true)
		setErrorMessage(null)
		setSuccessMessage(null)

		try {
			const token = await getToken()
			if (!token) throw new Error('Session expired. Please sign in again.')

			if (targetPlaylist === NEW_PLAYLIST_VALUE) {
				const title = newTitle.trim()
				if (!title) {
					setErrorMessage('Playlist title is required.')
					return
				}
				const created = await createPlaylist(token, {
					title,
					description: newDescription.trim() || undefined,
					video_ids: [videoId],
				})
				setSuccessMessage(`Added to new playlist "${created.title}".`)
			} else {
				await addVideosToPlaylist(token, Number(targetPlaylist), [videoId])
				const selected = playlists.find((item) => item.id.toString() === targetPlaylist)
				setSuccessMessage(`Added to "${selected?.title || 'playlist'}".`)
			}
		} catch (error) {
			console.error('Failed to add video to playlist', error)
			setErrorMessage('Could not add this video to a playlist.')
		} finally {
			setSubmitting(false)
		}
	}

	return (
		<>
			<Button
				type='button'
				variant={variant}
				size={size}
				className={className}
				onClick={openDialog}
			>
				<Plus className='h-4 w-4 mr-2' />
				Add to Playlist
			</Button>

			<Dialog open={open} onOpenChange={setOpen}>
				<DialogContent>
					<DialogHeader>
						<DialogTitle>Add to playlist</DialogTitle>
						<DialogDescription>
							Save {videoTitle ? `"${videoTitle}"` : 'this video'} in an existing
							playlist or create a new one.
						</DialogDescription>
					</DialogHeader>

					<form className='space-y-4' onSubmit={handleSubmit}>
						<div className='space-y-2'>
							<Label htmlFor='playlist-target'>Choose destination</Label>
							<Select
								value={targetPlaylist}
								onValueChange={(value) => {
									setTargetPlaylist(value)
									setSuccessMessage(null)
									setErrorMessage(null)
								}}
								disabled={loadingPlaylists || submitting}
							>
								<SelectTrigger id='playlist-target'>
									<SelectValue placeholder='Select a playlist' />
								</SelectTrigger>
								<SelectContent>
									{playlists.map((playlist) => (
										<SelectItem
											key={playlist.id}
											value={playlist.id.toString()}
										>
											{playlist.title}
										</SelectItem>
									))}
									<SelectItem value={NEW_PLAYLIST_VALUE}>
										Create new playlist
									</SelectItem>
								</SelectContent>
							</Select>
						</div>

						{targetPlaylist === NEW_PLAYLIST_VALUE && (
							<>
								<div className='space-y-2'>
									<Label htmlFor='new-playlist-title'>Playlist title</Label>
									<Input
										id='new-playlist-title'
										value={newTitle}
										onChange={(event) => setNewTitle(event.target.value)}
										placeholder='My favorite clips'
										disabled={submitting}
									/>
								</div>
								<div className='space-y-2'>
									<Label htmlFor='new-playlist-description'>Description (optional)</Label>
									<Textarea
										id='new-playlist-description'
										value={newDescription}
										onChange={(event) => setNewDescription(event.target.value)}
										placeholder='What is this playlist for?'
										disabled={submitting}
									/>
								</div>
							</>
						)}

						{errorMessage && <p className='text-sm text-destructive'>{errorMessage}</p>}
						{successMessage && <p className='text-sm text-green-600'>{successMessage}</p>}

						<DialogFooter>
							<Button
								type='button'
								variant='outline'
								onClick={() => setOpen(false)}
								disabled={submitting}
							>
								Cancel
							</Button>
							<Button type='submit' disabled={submitting || loadingPlaylists}>
								{submitting ? 'Saving...' : 'Save'}
							</Button>
						</DialogFooter>
					</form>
				</DialogContent>
			</Dialog>
		</>
	)
}

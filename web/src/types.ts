export interface User {
    id: number
    email: string
    name: string
  }
  
  export interface TokenResponse {
    access_token: string
    token_type: string
  }
  
  export interface EventItem {
    id: number
    title: string
    description: string
    event_date: string
    invite_code: string
    owner_id: number
    participants_count: number
  }
  
  export interface EventDetail extends EventItem {
    participants: User[]
  }

  export interface Movie {
    id: number
    event_id: number
    title: string
    genre: string
    poster_url: string | null
    added_by: number
  }
  
  export interface MovieResult extends Movie {
    votes: number
  }
  
  export interface Results {
    total_votes: number
    my_vote_movie_id: number | null
    winner: MovieResult | null
    tie: boolean
    movies: MovieResult[]
  }
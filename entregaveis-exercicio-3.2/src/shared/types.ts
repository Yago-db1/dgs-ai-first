export interface FeedbackRequest {
  queryId: string;
  rating: number;
  comment?: string;
  attendantEmail: string;
}

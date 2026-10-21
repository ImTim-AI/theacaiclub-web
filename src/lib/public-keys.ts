// Public, by design: the same anon key and Stripe publishable key already ship
// in /order and in the app binary. Neither grants anything without a signed-in
// user or a server-created PaymentIntent.
export const SUPABASE_URL = 'https://vtrsbxqlctmhkjnpdwdy.supabase.co';
export const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0cnNieHFsY3RtaGtqbnBkd2R5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDYyNjIzNzAsImV4cCI6MjA2MTgzODM3MH0.Nn65Q3E2Ly-j8bvn_SaR1TmKYnzcNye1wAiFu5ciiuk';
export const STRIPE_PK = 'pk_live_51IldPUGhY98XvWg6AWuEcFVQKjnJlhUhEKz7FtLHpGzKNUNWtC1pAOOJdDR5MxUbpxadbyphZ227MYXONw5TEhjM007TiGWv3f';

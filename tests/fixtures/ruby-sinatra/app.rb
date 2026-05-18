# Synthetic fixture — intentionally contains stub patterns for the audit harness.

require 'sinatra'

post '/charge' do
  # HIGH: route raises NotImplementedError in a user-reachable path.
  raise NotImplementedError, 'billing not wired yet'
end

get '/items' do
  # HIGH: response is a placeholder string with no real data.
  'TODO'
end

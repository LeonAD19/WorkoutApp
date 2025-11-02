import { render, screen } from '@testing-library/react';
import App from './App';

test('renders Flask + React connection message', () => {
  render(<App />);
  const heading = screen.getByText(/Flask \+ React Connected/i);
  expect(heading).toBeInTheDocument();
});

from bs4 import BeautifulSoup
import requests
import pandas as pd
from flask import Flask, render_template, request, jsonify


'''
take some data from the https://www.famousquotes123.com/public-quotes.html site. Less and more like the tutorial

'''
def scrape_quotes(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        quotes = []
        for quote_element in soup.find_all('blockquote'):
            quote_text = quote_element.find('q').text.strip()
            quote_author = quote_element.find('a', class_='authorname').text.strip()
            quotes.append({"text": quote_text, "author": quote_author})
        return quotes

    # this part should be added because of the venv support for the following code
    except requests.RequestException as e:
        print(f"Error fetching quotes: {e}")
        return []
    except AttributeError as e:
        print(f"Error parsing HTML: {e}")
        return []


# Scrape quotes and save to CSV
url = 'https://www.famousquotes123.com/public-quotes.html'
quotes = scrape_quotes(url)

# Convert to DataFrame
quotes_df = pd.DataFrame(quotes)

# Save to a CSV file
quotes_df.to_csv('quotes.csv', index=False)

# Print the DataFrame to verify
print(quotes_df)

# Create Flask app
app = Flask(__name__)

# Read and process the CSV file
def load_data():
    try:
        df = pd.read_csv('quotes.csv', header=0)
        # Add necessary columns for recommendation algorithm
        df['length'] = df['text'].apply(len)
        df['has_pronoun'] = df['text'].apply(lambda x: int('I' in x or 'my' in x))
        return df
    except FileNotFoundError:
        print("File not found. Make sure 'quotes.csv' exists.")
        return pd.DataFrame()
    except pd.errors.EmptyDataError:
        print("File is empty or cannot be read.")
        return pd.DataFrame()

df = load_data()

# Function to get quotes by author
def get_quotes_by_author(author):
    return df[df['author'] == author]

# Function to recommend quotes based on length and pronouns
def recommend_quotes(n=5):
	if df.empty:
		return []

	max_length = df['length'].max()
	if max_length == 0:
		df['weight'] = 1
	else:
		df['weight'] = (max_length - df['length'] + 1) + df['has_pronoun'] * max_length

	df['probability'] = df['weight'] / df['weight'].sum()

	# Ensure we do not request more samples than available
	n = min(n, len(df))

	sampled_df = df.sample(n, weights=df['probability'])
	return sampled_df.to_dict(orient='records')


@app.route('/')
def index():
    quotes = df.to_dict(orient='records')
    return render_template('index.html', quotes=quotes)


@app.route('/recommend', methods=['POST'])
def recommend():
	data = request.get_json()
	try:
		n = int(data.get('n', 5))  # Convert to integer
	except ValueError:
		n = 5  # Default to 5 if conversion fails

	# Ensure `n` is a positive integer
	if n <= 0:
		n = 5  # Default to 5 if `n` is not positive

	recommended_quotes = recommend_quotes(n)
	return jsonify(recommended_quotes)



if __name__ == '__main__':
    app.run(debug=True)

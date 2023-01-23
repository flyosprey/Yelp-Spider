<h2>This is crawler of yelp.com</h2>

<h3>It craws the following params:</h3>
<ul>
    <li>Business name</li>
    <li>Business rating</li>
    <li>Number of reviews</li>
    <li>Business yelp url</li>
    <li>Business website</li>
    <li>List of first 5 reviews, for each review:</li>
<ul>
    <li>Reviewer name</li>
    <li>Reviewer location</li>
    <li>Review date</li>
</ul>
</ul>

<h3>Before running spider need to set required search parameters in required_params.json.<br>
The file locate in spider directory</h3>
<p>Parameters:</p>
<ul>
    <li>Category</li>
    <li>Location</li>
</ul>

<p>Result can be written in .json file</p>

<h3>To run spider use the following command:</h4>
<p><b>scrapy crawl yelp -O business_data_output.json</b></p>
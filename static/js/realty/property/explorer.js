document.addEventListener('DOMContentLoaded', function () {
	var base_url = '/api/properties/';

	document.getElementById('search').addEventListener('click', function () {
		var category = document.querySelector('[name=category]').value;
		var purpose = document.querySelector('[name=purpose]').value;
		var address = document.querySelector('[name=address]').value;

		if (!category && !purpose && !address) return;

		var url = base_url+'?';

		if (category) url+= 'category='+category+'&';
		if (purpose) url+= 'purpose='+purpose+'&';
		if (address) url+= 'address='+address+'&';

		getData(url);
	});

	var getData = function (url) {		
		$.get(url, function (data) {
			console.log(data);
		});
	}

});
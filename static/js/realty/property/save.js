document.addEventListener('DOMContentLoaded', function () {
	var saveButton = document.querySelector('.save-btn');
	if (saveButton) {
		saveButton.addEventListener('click', function (e) {
			e.preventDefault();
			if (!this.hasAttribute('saved')) {
				document.getElementById('log_form').submit();
			}
		});		
	}
});
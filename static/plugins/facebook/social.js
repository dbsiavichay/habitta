var fb = document.getElementById('facebook');
if(fb) {
    fb.addEventListener('click', function(event) {
        event.preventDefault();
        checkLogin();
    });    
}


function checkLogin() {
    FB.getLoginStatus(function (response){                
        if (response.status === 'connected') {
            document.getElementById('socialProvider').value = 'facebook';
            document.getElementById('socialToken').value = response.authResponse.accessToken;
            document.getElementById('socialForm').submit();
        } else {
            FB.login(function (response) {
                checkLogin();
            });
        } 
    });
}

var tw = document.getElementById('twitter');
if(tw) {
    tw.addEventListener('click', function (event) {
        event.preventDefault();
        document.getElementById('socialProvider').value = 'twitter';            
        document.getElementById('socialForm').submit();
    });
}
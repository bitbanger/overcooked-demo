// Persistent network connection that will be used to transmit real-time data
var socket = io();

$(document).ready(function() {
});

/* * * * * * * * * * * * * * * * 
 * Button click event handlers *
 * * * * * * * * * * * * * * * */

$(function() {
    $('#create').click(function () {
        params = arrToJSON($('form').serializeArray());
        params.layouts = [params.layout]
        data = {
            "params" : params,
            "game_name" : "overcooked",
            "create_if_not_found" : false,
            "chatlog_filename" : $('#chatlogfnbox').val()
        };
        socket.emit("create", data);
        $('#waiting').show();
        $('#join').hide();
        $('#join').attr("disabled", true);
        $('#create').hide();
        $('#create').attr("disabled", true)
        $('#chatlogfnbox').hide();
        $('#chatlogfnbox').attr("disabled", true)
        $("#instructions").hide();
        $('#tutorial').hide();
		var urlParams = new URLSearchParams(window.location.search);
		if (urlParams.get('practice') == 'true') {
			console.log('practice mode');
			$('#undo').hide();
			$('#undo').attr("disabled", true);
			$('#survey').hide();
			$('#survey').attr("disabled", true);
			$('#leftpanel').hide();
		}
    });
});

$(function() {
    $('#join').click(function() {
        socket.emit("join", {});
        $('#join').attr("disabled", true);
        $('#create').attr("disabled", true);
    });
	setTimeout(function() {
		var urlParams = new URLSearchParams(window.location.search);
		if (urlParams.get('practice') == 'true') {
			$('#create').trigger('click');
		}
	}, 100);
});

$(function() {
    $('#leave').click(function() {
        socket.emit('leave', {});
        $('#leave').attr("disabled", true);
    });
});

$(function() {
    $('#undo').click(function() {
        socket.emit('undo', {});
    });
});

$(function() {
    $('#survey').click(function() {
		if (confirm('Are you done teaching VAL? If so, click OK to move on to the survey.')) {
			window.open('https://gatech.co1.qualtrics.com/jfe/form/SV_39qOsSe91BNmnqu?participantid=' + $('#uuid').attr('value'), '_blank');
		}
    });
});





/* * * * * * * * * * * * * 
 * Socket event handlers *
 * * * * * * * * * * * * */

window.intervalID = -1;
window.spectating = true;

socket.on('waiting', function(data) {
    // Show game lobby
    $('#error-exit').hide();
    $('#waiting').hide();
    $('#game-over').hide();
    $('#instructions').hide();
    $('#tutorial').hide();
    $("#overcooked").empty();
    $('#lobby').show();
    $('#join').hide();
    $('#join').attr("disabled", true)
    $('#create').hide();
    $('#create').attr("disabled", true)
    // $('#leave').show();
    // $('#leave').attr("disabled", false);
    $('#leftpanel').show();
    $('#undo').show();
    $('#undo').attr("disabled", false);
    $('#survey').show();
    $('#survey').attr("disabled", false);
    if (!data.in_game) {
        // Begin pinging to join if not currently in a game
        if (window.intervalID === -1) {
            window.intervalID = setInterval(function() {
                socket.emit('join', {});
            }, 1000);
        }
    }
});

socket.on('creation_failed', function(data) {
    // Tell user what went wrong
    let err = data['error']
    $("#overcooked").empty();
    $('#lobby').hide();
    $("#instructions").show();
    $('#tutorial').show();
    $('#waiting').hide();
    // $('#join').show();
    // $('#join').attr("disabled", false);
    $('#create').show();
    $('#create').attr("disabled", false);
    $('#overcooked').append(`<h4>Sorry, game creation code failed with error: ${JSON.stringify(err)}</>`);
});

socket.on('start_game', function(data) {
    // Hide game-over and lobby, show game title header
    if (window.intervalID !== -1) {
        clearInterval(window.intervalID);
        window.intervalID = -1;
    }
    graphics_config = {
        container_id : "overcooked",
        start_info : data.start_info
    };
    window.spectating = data.spectating;
    $('#error-exit').hide();
    $("#overcooked").empty();
    $('#game-over').hide();
    $('#lobby').hide();
    $('#waiting').hide();
    $('#join').hide();
    $('#join').attr("disabled", true);
    $('#create').hide();
    $('#create').attr("disabled", true)
    $("#instructions").hide();
    $('#tutorial').hide();
    // $('#leave').show();
    // $('#leave').attr("disabled", false)
    $('#leftpanel').show();
    $('#undo').show();
    $('#undo').attr("disabled", false)
    $('#survey').show();
    $('#survey').attr("disabled", false)
    $('#game-title').show();
	var urlParams = new URLSearchParams(window.location.search);
	if (urlParams.get('practice') == 'true') {
		console.log('practice mode');
		$('#undo').hide();
		$('#undo').attr("disabled", true);
		$('#survey').hide();
		$('#survey').attr("disabled", true);
		$('#leftpanel').hide();
		$('#toppanel').append($.parseHTML("<div style='background: white; border-radius: 3px; border: 1px black solid; padding: 5px 5px 5px 5px;'><p>Try to make onion soup with just <strong>one</strong> onion, instead of three. Click <a href='/valtutorial1'><strong>here</strong></a> to review the game basics, or <a href='/valtutorial2'><strong>here</strong></a> to move on once you've finished.</p></div>"));
	}
    
    if (!window.spectating) {
        enable_key_listener();
    }
    
    graphics_start(graphics_config);
});

socket.on('reset_game', function(data) {
    graphics_end();
    if (!window.spectating) {
        disable_key_listener();
    }
    
    $("#overcooked").empty();
    $("#reset-game").show();
    setTimeout(function() {
        $("reset-game").hide();
        graphics_config = {
            container_id : "overcooked",
            start_info : data.state
        };
        if (!window.spectating) {
            enable_key_listener();
        }
        graphics_start(graphics_config);
    }, data.timeout);
});

socket.on('state_pong', function(data) {
    // Draw state update
    drawState(data['state']);
});

socket.on('end_game', function(data) {
    // Hide game data and display game-over html
    graphics_end();
    if (!window.spectating) {
        disable_key_listener();
    }
    $('#game-title').hide();
    $('#game-over').show();
    // $("#join").show();
    // $('#join').attr("disabled", false);
    $("#create").show();
    $('#create').attr("disabled", false)
    $("#instructions").show();
    $('#tutorial').show();
    $("#leave").hide();
    $('#leave').attr("disabled", true)
    
    // Game ended unexpectedly
    if (data.status === 'inactive') {
        $('#error-exit').show();
    }
});

socket.on('end_lobby', function() {
    // Hide lobby
    $('#lobby').hide();
    // $("#join").show();
    // $('#join').attr("disabled", false);
    $("#create").show();
    $('#create').attr("disabled", false)
    $("#leave").hide();
    $('#leave').attr("disabled", true)
    $("#instructions").show();
    $('#tutorial').show();

    // Stop trying to join
    clearInterval(window.intervalID);
    window.intervalID = -1;
})


/* * * * * * * * * * * * * * 
 * Game Key Event Listener *
 * * * * * * * * * * * * * */

function enable_key_listener() {
    $(document).on('keydown', function(e) {
        let action = 'STAY'
	switch (e.which) {
	    case 37: // left
		action = 'LEFT';
		break;

	    case 38: // up
		action = 'UP';
		break;

	    case 39: // right
		action = 'RIGHT';
		break;

	    case 40: // down
		action = 'DOWN';
		break;

	    case 32: //space
		action = 'SPACE';
		break;

	    default: // exit this handler for other keys
		return; 
	}
	if($(".msger-input").is(":focus")) {
		action = 'STAY';
	} else {
        	e.preventDefault();
	}
        socket.emit('action', { 'action' : action });
    });
};

function disable_key_listener() {
    $(document).off('keydown');
};


/* * * * * * * * * * *
 * Utility Functions *
 * * * * * * * * * * */

var arrToJSON = function(arr) {
    let retval = {}
    for (let i = 0; i < arr.length; i++) {
        elem = arr[i];
        key = elem['name'];
        value = elem['value'];
        retval[key] = value;
    }
    return retval;
};

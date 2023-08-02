// var socket = io();

const msgerForm = get(".msger-inputarea");
const msgerInput = get(".msger-input");
var msgerChat = get(".msger-chat");

const BOT_MSGS = [
"Hi, how are you?",
"Ohh... I can't understand what you trying to say. Sorry!",
"I like to play games... But I don't know how to play!",
"Sorry if my answers are not relevant. :))",
"I feel sleepy! :("];


// Icons made by Freepik from www.flaticon.com
const BOT_IMG = "static/images/val_icon.svg";
const PERSON_IMG = "static/images/usr_icon.svg";
const BOT_NAME = "VAL";
const PERSON_NAME = "You";

socket.on('valmsg', function(data) {
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid) {
		botResponse(data['msg']);
	}
});

socket.on('get_chat_html_state', function(data) {
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid) {
		socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
	}
});

socket.on('set_chat_html_state', function(data) {
	console.log('in set state');
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid) {
		// socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
		// console.log('replacing ' + $('.msger-chat').html());
		// console.log('with ' + data['html']);

		var tempDom = $('<output>').append($.parseHTML('<main class="msger-chat">' + data['html'] + '</main>'));

		var oldMsgCount = $('.msger-chat').children().size();
		var newMsgCount = tempDom.children().children().size();

		console.log('old has ' + oldMsgCount + ', new has ' + newMsgCount);

		console.log($('.msger-chat').children().slice(-(oldMsgCount-newMsgCount)));

		console.log($('.msger-chat').size() + ' msger-chats');

		var children = 0;
		if (oldMsgCount > newMsgCount) {
			console.log('herejs1');
			$('.msger-chat').children().slice(-(oldMsgCount-newMsgCount)).fadeOut("slow").promise().done(function() {
				console.log('herejs1.5');
				// replace the HTML post-fadeout (this resets button states and stuff)
				$('.msger-chat').replaceWith($.parseHTML('<main class="msger-chat">' + data['html'] + '</main>'));
				// the problem is we need to scroll all the way down
				$('.msger-chat').scrollTop($('.msger-chat')[0].scrollHeight);
				// reset the msgerChat reference to the new DOM element for event handling
				msgerChat = get(".msger-chat");
				// notify app.py that we can reset the game state now that the fade animation is done
				socket.emit('undo_post_fadeout', {});
			});
		} else {
			$('.msger-chat').children().last().fadeTo("slow", 0.0).promise().done(function() {
				console.log('herejs2');
				// replace the HTML post-fadeout (this resets button states and stuff)
				$('.msger-chat').replaceWith($.parseHTML('<main class="msger-chat">' + data['html'] + '</main>'));
				// the problem is we need to scroll all the way down
				$('.msger-chat').scrollTop($('.msger-chat')[0].scrollHeight);
				// reset the msgerChat reference to the new DOM element for event handling
				msgerChat = get(".msger-chat");
				// notify app.py that we can reset the game state now that the fade animation is done
				socket.emit('undo_post_fadeout', {});
			});
		}


		// $('.msger-chat').children().slice(-(oldMsgCount-newMsgCount)).fadeOut("slow", function() {
		// $('.msger-chat').fadeOut("slow", function() {
		// $('.msger-chat').fadeTo("slow", 0.0, function() {
		// $('.msger-chat').replaceWith($.parseHTML('<main class="msger-chat">' + data['html'] + '</main>'));
	}
});

socket.on('webchat_undo', function(data) {
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid) {
		// var num_player_msgs = 
	}
});

socket.on('tell_web_game_uuid', function(data) {
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid) {
		$(document).children('html').children('head').append('<data id="uuid" value="' + data['uuid'] + '" />');
	}
});

$(document).ready(function() {
	console.log('setting id');
	var id = Math.floor(Math.random() * 10000000);
	socket.emit('setwebmuxid', {'id': id});
	$(document).children('html').children('head').append('<data id="webmuxid" value="' + id + '" />');
});

$(document).ready(function() {
	document.addEventListener('click', function(event) {
		if(event.target) {
			var caught = true;

			if (event.target.id == 'msger-yes-btn') {
				socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
				socket.emit('message', {'msg': 'Y'});
			} else if (event.target.id == 'msger-no-btn') {
				socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
				socket.emit('message', {'msg': 'N'});
			} else if (event.target.id == 'msger-maybe-btn') {
				socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
				socket.emit('message', {'msg': 'M'});
			} else if (event.target.id == 'msger-bad-action-btn') {
				socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
				socket.emit('message', {'msg': 'action'});
			} else if (event.target.id == 'msger-bad-args-btn') {
				socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
				socket.emit('message', {'msg': 'args'});
			} else if (event.target.id == 'msger-bad-both-btn') {
				socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
				socket.emit('message', {'msg': 'both'});
			} else {
				caught = false;
			}

			if (caught) {
				event.preventDefault();
				$(event.target).prop("disabled", true);
				$(event.target).siblings(":button").prop("disabled", true);
				$(event.target).siblings(":button").css("background-color", "gray");
			}
		}
	});
});

$(document).ready(function() {
	document.addEventListener('change', function(event) {
		if(event.target) {
			if (event.target.className == 'msger-act-radio') {
				event.preventDefault();
				// console.log(event.target.value);
				// $(event.target).prop("disabled", true);
				socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
				$(event.target).siblings(".msger-act-radio").prop("disabled", true);
				socket.emit('message', {'msg': event.target.value});
			}
		}
	});
});

$(document).ready(function() {
	document.addEventListener('submit', function(event) {
		var webmuxid = $('#webmuxid').attr('value');
		if(event.target) {
			if (event.target.className == "argdropdownform") {
				event.preventDefault();
				var str = '';
				$(event.target).children('.argdropdown').each(function() {
					str = str + '\t' + $(this).val();
				});
				// console.log(str);
				socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
				socket.emit('message', {'msg': str});
				socket.emit('disable_chat_input', {'id': webmuxid, 'placeholder': 'Please wait...', 'send_btn_text': 'Send'});

				$(event.target).children('.argdropdown').prop("disabled", true);
				$(event.target).children('.msger-yes-btn').prop("disabled", true);
				$(event.target).children('.msger-yes-btn').css("background-color", "gray");
				// $(event.target).prop("disabled", true);
				// $(event.target).siblings(".msger-act-radio").prop("disabled", true);
				// socket.emit('message', {'msg': event.target.value});
			} else if (event.target.className == "newargdropdownform") {
				event.preventDefault();
				var str = '';
				$(event.target).children('.newargdropdown').each(function() {
					str = str + '\t' + $(this).val();
				});
				socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
				socket.emit('message', {'msg': str});

				$(event.target).children('.newargdropdown').prop("disabled", true);
				$(event.target).children('.msger-add-btn').prop("disabled", true);
				$(event.target).children('.msger-add-btn').css("background-color", "gray");
				$(event.target).children('.msger-remove-btn').prop("disabled", true);
				$(event.target).children('.msger-remove-btn').css("background-color", "gray");
				$(event.target).children('.msger-submit-btn').prop("disabled", true);
				$(event.target).children('.msger-submit-btn').css("background-color", "gray");
			}
		}
	});
});

$(document).ready(function() {
	document.addEventListener('click', function(event) {
		var template = '<select class="newargdropdown" id="newargdropdown"><option value="pot">pot</option><option value="onion">onion</option><option value="tomato">tomato</option><option value="dropoff">dropoff</option><option value="plate">plate</option></select>';

		if(event.target) {
			var caught = true;
			if (event.target.className == "msger-add-btn") {
				if($(event.target).parent().children(".newargdropdown").size() > 0) {
					$(event.target).parent().children(".newargdropdown").last().after('<b class="comma"> , </b>');
				}

				$(event.target).parent().children("b.rightparen").before(template);
			} else if (event.target.className == "msger-remove-btn") {
				if($(event.target).parent().children(".newargdropdown").size() > 1) {
					$(event.target).parent().children(".newargdropdown").last().remove();
					$(event.target).parent().children("b.comma").last().remove();
				} else {
					$(event.target).parent().children(".newargdropdown").last().remove();
				}
			} else {
				caught = false;
			}
		}

		if (caught) {
			event.preventDefault();
		}
	});
});

msgerForm.addEventListener("submit", event => {
  event.preventDefault();

  const msgText = msgerInput.value;
  if (!msgText) return;

  if ( msgText != 'undo' && msgText != 'save' && msgText != 'load' ) {
    socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
  }
  socket.emit('message', {'msg': msgText})

  if(msgText != "load" && msgText != "save" && msgText != "undo") {
    appendMessage(PERSON_NAME, PERSON_IMG, "right", msgText);
  }
  msgerInput.value = "";
});

socket.on('premovemsg', function(data) {
    console.log('got premove "' + data['msg'] + '"');
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid && !data['silenced']) {
		socket.emit('return_chat_html_state', {'state': $('.msger-chat').html()});
		if(data['msg'] != "load" && data['msg'] != "save" && data['msg'] != "undo") {
			appendMessage(PERSON_NAME, PERSON_IMG, "right", data['msg']);
		}
	}
});

socket.on('premove_undo', function(data) {
    console.log('got premove undo');
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid) {
		socket.emit('undo', {});
	}
});

socket.on('re_enable_undo', function(data) {
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid) {
		$('#undo').prop('disabled', false);
	}
});

socket.on('disable_undo', function(data) {
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid) {
		$('#undo').prop('disabled', true);
	}
});

socket.on('disable_chat_input', function(data) {
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid) {
		$('#msger-input').prop('disabled', true);
		$('#msger-input').prop('placeholder', data['placeholder']);
		$('#msger-input').prop('style', 'background: #bbb;');

		$('#msger-send-btn').prop('disabled', true);
		$('#msger-send-btn').text('➤\n' + data['send_btn_txt']);
		$('#msger-send-btn').html($('#msger-send-btn').html().replace(/\n/g,'<br/>'));
		$('#msger-send-btn').prop('style', 'background: gray;');
	}
});

socket.on('update_knowledge_panel', function(data) {
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid) {
		$("#knowledgepanel").html($(".currentlyknown").last().html());
	}
})

socket.on('enable_chat_input', function(data) {
	var webmuxid = $('#webmuxid').attr('value');
	if (data['id'] == webmuxid) {
		$('#msger-input').prop('disabled', false);
		$('#msger-input').prop('placeholder', 'Enter your message...');
		$('#msger-input').prop('style', 'background: #ddd;');
		$('#msger-input').focus();

		$('#msger-send-btn').prop('disabled', false);
		$('#msger-send-btn').text('➤\nSend');
		$('#msger-send-btn').html($('#msger-send-btn').html().replace(/\n/g,'<br/>'));
		$('#msger-send-btn').removeAttr('style');
	}
});

function appendMessage(name, img, side, text) {
  //   Simple solution for small apps
  const msgHTML = `
    <div class="msg ${side}-msg">
      <div class="msg-img" style="background-image: url(${img})"></div>

      <div class="msg-bubble">
        <div class="msg-info">
          <div class="msg-info-name">${name}</div>
          <div class="msg-info-time">${formatDate(new Date())}</div>
        </div>

        <div class="msg-text">${text}</div>
      </div>
    </div>
  `;

  msgerChat.insertAdjacentHTML("beforeend", msgHTML);
  msgerChat.scrollTop += 500;
}

function botResponse(msgText) {
  // const delay = msgText.split(" ").length * 100;

  // setTimeout(() => {
    appendMessage(BOT_NAME, BOT_IMG, "left", msgText);
  // }, delay);
}

// Utils
function get(selector, root = document) {
  return root.querySelector(selector);
}

function formatDate(date) {
  const h = "0" + date.getHours();
  const m = "0" + date.getMinutes();

  return `${h.slice(-2)}:${m.slice(-2)}`;
}

function random(min, max) {
  return Math.floor(Math.random() * (max - min) + min);
}

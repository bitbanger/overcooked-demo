// var socket = io();

const msgerForm = get(".msger-inputarea");
const msgerInput = get(".msger-input");
const msgerChat = get(".msger-chat");

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
	botResponse(data['msg']);
});

$(document).ready(function() {
	document.addEventListener('click', function(event) {
		if(event.target) {
			var caught = true;

			if (event.target.id == 'msger-yes-btn') {
				socket.emit('message', {'msg': 'Y'});
			} else if (event.target.id == 'msger-no-btn') {
				socket.emit('message', {'msg': 'N'});
			} else if (event.target.id == 'msger-bad-action-btn') {
				socket.emit('message', {'msg': 'action'});
			} else if (event.target.id == 'msger-bad-args-btn') {
				socket.emit('message', {'msg': 'args'});
			} else if (event.target.id == 'msger-bad-both-btn') {
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
				$(event.target).siblings(".msger-act-radio").prop("disabled", true);
				socket.emit('message', {'msg': event.target.value});
			}
		}
	});
});

msgerForm.addEventListener("submit", event => {
  event.preventDefault();

  const msgText = msgerInput.value;
  if (!msgText) return;

  socket.emit('message', {'msg': msgText})

  appendMessage(PERSON_NAME, PERSON_IMG, "right", msgText);
  msgerInput.value = "";
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

/*
* This assumes a type of dom structure to make divs that can be stretched
* horizontally using a slider between them. The dom structure consists of an
* outer div with flex display, containing a sequence of divs that have classes
* resizable, resizer, resizable, ... , resizer, resizable
* starting and ending with resizable with resizers in between. It assumes css
* of the form:
* .resizer {
*     background-color: #cbd5e0;
*     cursor: ew-resize;
*     width: 4px;
*     border-left: 1px solid #888;
*     border-right: 1px solid #888;
* }
*/
var resizer = null;
var leftSide = null;
var rightSide = null;
var leftWidth = 0;
var rightWidth = 0;
document.addEventListener('DOMContentLoaded', function () {
    let x = 0;
    let y = 0;
    
    // Handle the mousedown event
    // that's triggered when user drags the resizer
    const mouseDownHandler = function (e) {
        resizer = e.target;
        // Get the current mouse position
        x = e.clientX;
        y = e.clientY;
        leftSide = resizer.previousElementSibling;
        rightSide = resizer.nextElementSibling;
        //              console.log(leftSide);
        leftWidth = leftSide.getBoundingClientRect().width;
        rightWidth = rightSide.getBoundingClientRect().width;
        // Attach the listeners to `document`
        document.addEventListener('mousemove', mouseMoveHandler);
        document.addEventListener('mouseup', mouseUpHandler);
    };

    const mouseMoveHandler = function (e) {
        // How far the mouse has been moved
        const dx = e.clientX - x;
        const parentWidth = resizer.parentNode.getBoundingClientRect().width;
        const newLeftWidth = ((leftWidth + dx) * 100) / parentWidth;
        leftSide.style.width = `${newLeftWidth}%`;
        const newRightWidth = ((rightWidth - dx) * 100) / parentWidth;
        rightSide.style.width = `${newRightWidth}%`;

        resizer.style.cursor = 'col-resize';
        document.body.style.cursor = 'col-resize';

        leftSide.style.userSelect = 'none';
        leftSide.style.pointerEvents = 'none';

        rightSide.style.userSelect = 'none';
        rightSide.style.pointerEvents = 'none';
    };

    const mouseUpHandler = function (e) {
        resizer.style.removeProperty('cursor');
        document.body.style.removeProperty('cursor');

        leftSide.style.removeProperty('user-select');
        leftSide.style.removeProperty('pointer-events');

        rightSide.style.removeProperty('user-select');
        rightSide.style.removeProperty('pointer-events');

        // Remove the handlers of `mousemove` and `mouseup`
        document.removeEventListener('mousemove', mouseMoveHandler);
        document.removeEventListener('mouseup', mouseUpHandler);
    };

    // Attach the handler
    document.querySelectorAll('.resizer').forEach((el) => {
        el.addEventListener('mousedown', mouseDownHandler);
    });
});

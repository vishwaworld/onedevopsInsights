/*******************************************************************************
 * Copyright 2017 Cognizant Technology Solutions
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License.  You may obtain a copy
 * of the License at
 * 
 *   http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations under
 * the License.
 ******************************************************************************/

//// <reference path="../../../_all.ts" />

module ISightApp {
    export class QuickViewDialogController {
        static $inject = ['$mdDialog', '$route', '$location'];
        constructor(private $mdDialog, private $route, private $location) {
            this.buttonText = 'OK';
            this.statusObject = this['locals'].statusObject;
          
        }
        notification: string;
        buttonText: string;
        statusObject;
        addedApplicationName: string;
        
        myChartObject = {
  "type": "BarChart",
  "data": {
    "cols": [
      {
        "id": "t",
        "label": "week",
        "type": "string"
      },
      {
        "id": "s",
        "label": "avgbuildtime",
        "type": "number"
      }
    ],
    "rows": [
      {
        "c": [
          {
            "v": "week1"
          },
          {
            "v": 60
          }
        ]
      },
      {
        "c": [
          {
            "v": "week2"
          },
          {
            "v": 50
          }
        ]
      }
    ]
  },
  "options": {
    "title": "Average build over 2 weeks"
  }
};
        hide(): void {
            this.$mdDialog.hide();
        }
        cancel(): void {
            this.$mdDialog.cancel();
        }
        finalConfirmation(): void {
            if (this.buttonText === 'Yes') {
                this.statusObject.status = true;
                this.hide();
            }
            else if (this.buttonText === 'OK') {
                this.notification = 'Are you sure you wish to add the New Access Group ' ;
                this.buttonText = 'Yes';
            }
        }
    }
}

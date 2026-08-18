-- Taicang 1F (D-1012*)
INSERT OR IGNORE INTO rooms(room_id, campus, building, floor, name, capacity, min_attendance, features, is_active)
VALUES
('D-1012D','taicang','D',1,'D-1012D',5,2,'["whiteboard"]',1),
('D-1012E','taicang','D',1,'D-1012E',5,2,'["whiteboard"]',1),
('D-1012F','taicang','D',1,'D-1012F',5,2,'["tv"]',1),
('D-1012G','taicang','D',1,'D-1012G',5,2,'["tv","whiteboard"]',1),
('D-1012H','taicang','D',1,'D-1012H',5,2,'[]',1),
('D-1012J','taicang','D',1,'D-1012J',5,2,'[]',1);

-- Taicang 2F (D-2016*)
INSERT OR IGNORE INTO rooms(room_id, campus, building, floor, name, capacity, min_attendance, features, is_active)
VALUES
('D-2016A','taicang','D',2,'D-2016A',5,2,'[]',1),
('D-2016B','taicang','D',2,'D-2016B',5,2,'[]',1),
('D-2016C','taicang','D',2,'D-2016C',5,2,'[]',1),
('D-2016D','taicang','D',2,'D-2016D',5,2,'[]',1),
('D-2016E','taicang','D',2,'D-2016E',5,2,'[]',1),
('D-2016F','taicang','D',2,'D-2016F',5,2,'[]',1);

-- Taicang 3F (D-3016*)
INSERT OR IGNORE INTO rooms(room_id, campus, building, floor, name, capacity, min_attendance, features, is_active)
VALUES
('D-3016A','taicang','D',3,'D-3016A',5,2,'[]',1),
('D-3016B','taicang','D',3,'D-3016B',5,2,'[]',1),
('D-3016C','taicang','D',3,'D-3016C',5,2,'[]',1),
('D-3016D','taicang','D',3,'D-3016D',5,2,'[]',1),
('D-3016E','taicang','D',3,'D-3016E',5,2,'[]',1),
('D-3016F','taicang','D',3,'D-3016F',5,2,'[]',1);

-- Sports facilities use the same conflict and policy engine.
INSERT OR IGNORE INTO rooms(
  room_id, campus, building, floor, name, capacity, min_attendance,
  features, is_active, category, activity
)
VALUES
('BAD-01','taicang','Sports Centre',1,'Badminton Court 01',4,2,'["indoor","equipment-rental"]',1,'sports','badminton'),
('BAD-02','taicang','Sports Centre',1,'Badminton Court 02',4,2,'["indoor","equipment-rental"]',1,'sports','badminton'),
('TENNIS-01','taicang','Outdoor Courts',1,'Tennis Court 01',4,2,'["outdoor","floodlights"]',1,'sports','tennis'),
('BASKET-01','taicang','Sports Centre',1,'Basketball Court 01',10,4,'["indoor","full-court"]',1,'sports','basketball');

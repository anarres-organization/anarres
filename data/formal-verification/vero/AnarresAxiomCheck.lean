import Lean

/-!
Trusted axiom and statement check for fresh Vero grading.

Vero reads its axiom report from Lake output, and any model code that runs while a
model module is built or imported can forge that output. This checker never imports a
model module. It reads the compiled `.olean` files as data, sends the target theorems
and everything they depend on back through the kernel, computes axioms from the
kernel-checked environment, and requires each target theorem's statement, and every
declaration its proof rests on that the reference also declares, to equal a reference
build of the untouched task. Every axiom outside the toolchain must be the reference's
own declaration, so a model cannot redeclare a trusted axiom's name or change what a
trusted axiom's statement means.

Usage: `lean --run AnarresAxiomCheck.lean <nonce> <request.json>`, for one Vero
axiom-check file. The request names the submission and reference library directories,
the file's imports, its target theorems, and the allowed axioms. The checker prints one
JSON object per theorem and then `ANARRES-AXIOM-CHECK-COMPLETE <nonce> <count>`. A
reference build that cannot be read exits with status 3 after
`ANARRES-AXIOM-CHECK-REFERENCE-ERROR <nonce>`.
-/

open Lean

structure Loaded where
  constants : Std.HashMap Name ConstantInfo := {}
  modules : Std.HashMap Name Name := {}
  core : Array Import := #[]
  seen : NameSet := {}

/-- Read a module closure as data. Core modules come only from the toolchain. -/
partial def load (core libraries : SearchPath) (mod : Name) : StateT Loaded IO Unit := do
  if (← get).seen.contains mod then return
  modify fun s => { s with seen := s.seen.insert mod }
  if (← core.findWithExt "olean" mod).isSome then
    modify fun s => { s with core := s.core.push { module := mod } }
    return
  let some file ← libraries.findWithExt "olean" mod
    | throw <| IO.userError s!"module not found: {mod}"
  let (data, _) ← readModuleData file
  if data.isModule then
    throw <| IO.userError s!"module-system olean is not supported: {mod}"
  for dependency in data.imports do
    load core libraries dependency.module
  for info in data.constants do
    if (← get).constants.contains info.name then
      throw <| IO.userError s!"duplicate constant: {info.name}"
    modify fun s => { s with
      constants := s.constants.insert info.name info
      modules := s.modules.insert info.name mod }

def loadAll (core libraries : SearchPath) (roots : Array Name) : IO Loaded := do
  let (_, loaded) ← (roots.forM (load core libraries)).run {}
  return loaded

/-- Every submission constant a set of targets depends on, with whole inductive blocks. -/
partial def closure (constants : Std.HashMap Name ConstantInfo) (name : Name) :
    StateM NameSet Unit := do
  if (← get).contains name then return
  let some info := constants[name]? | return
  modify (·.insert name)
  for used in info.getUsedConstantsAsSet do
    closure constants used
  match info with
  | .inductInfo value => (value.all ++ value.ctors).forM (closure constants)
  | .ctorInfo value => closure constants value.induct
  | .recInfo value => value.all.forM (closure constants)
  | _ => pure ()

def closureNames (constants : Std.HashMap Name ConstantInfo) (targets : Array Name) : NameSet :=
  let ((), names) := (targets.forM (closure constants)).run {}
  names

def restrict (constants : Std.HashMap Name ConstantInfo) (targets : Array Name) :
    Std.HashMap Name ConstantInfo :=
  (closureNames constants targets).foldl (fun map name => map.insert name constants[name]!) {}

/-- A reference value that uses `sorry` is a slot the model fills. -/
def slotOwned (info : ConstantInfo) : Bool :=
  match info.value? (allowOpaque := true) with
  | some value => value.getUsedConstants.contains ``sorryAx
  | none => false

/-- Require a statement's protected dependencies to be unchanged from the reference. -/
partial def sameStatement (reference submission : Std.HashMap Name ConstantInfo)
    (name : Name) : StateT NameSet (Except String) Unit := do
  if (← get).contains name then return
  modify (·.insert name)
  let some expected := reference[name]?
    | if submission.contains name then throw s!"statement depends on new constant {name}"
      else return
  let some actual := submission[name]? | throw s!"protected constant is missing: {name}"
  unless expected.levelParams == actual.levelParams && expected.type == actual.type do
    throw s!"type of {name} changed"
  let follow (e : Expr) := e.getUsedConstants.forM (sameStatement reference submission)
  let sameValue (e a : Expr) : StateT NameSet (Except String) Unit := do
    unless slotOwned expected do
      unless e == a do throw s!"definition of {name} changed"
      follow e
  follow expected.type
  match expected, actual with
  | .thmInfo _, .thmInfo _ | .axiomInfo _, .axiomInfo _ | .quotInfo _, .quotInfo _ => pure ()
  | .defnInfo e, .defnInfo a => sameValue e.value a.value
  | .opaqueInfo e, .opaqueInfo a => sameValue e.value a.value
  | .inductInfo e, .inductInfo a =>
    unless e.ctors == a.ctors && e.numParams == a.numParams && e.numIndices == a.numIndices do
      throw s!"inductive {name} changed"
    e.ctors.forM (sameStatement reference submission)
  | .ctorInfo _, .ctorInfo _ | .recInfo _, .recInfo _ => pure ()
  | _, _ => throw s!"kind of {name} changed"

/-- A constant the reference also declares must be unchanged, unless it is a slot. -/
def sameConstant (expected actual : ConstantInfo) : Except String Unit := do
  let name := expected.name
  unless expected.levelParams == actual.levelParams && expected.type == actual.type do
    throw s!"type of {name} changed"
  let sameValue (e a : Expr) : Except String Unit :=
    unless slotOwned expected || e == a do throw s!"definition of {name} changed"
  match expected, actual with
  | .thmInfo _, .thmInfo _ | .axiomInfo _, .axiomInfo _ | .quotInfo _, .quotInfo _
  | .ctorInfo _, .ctorInfo _ | .recInfo _, .recInfo _ => pure ()
  | .defnInfo e, .defnInfo a => sameValue e.value a.value
  | .opaqueInfo e, .opaqueInfo a => sameValue e.value a.value
  | .inductInfo e, .inductInfo a =>
    unless e.ctors == a.ctors && e.numParams == a.numParams && e.numIndices == a.numIndices do
      throw s!"inductive {name} changed"
  | _, _ => throw s!"kind of {name} changed"

def axiomsOf (env : Environment) (name : Name) : Array Name :=
  let (_, state) := ((CollectAxioms.collect name).run env).run {}
  state.axioms

/-- An axiom outside the toolchain must be the reference's own declaration. -/
def trustedAxiom (reference submission : Loaded) (name : Name) : Bool :=
  match submission.constants[name]? with
  | none => true
  | some actual =>
    match reference.constants[name]? with
    | some (.axiomInfo expected) =>
      expected.levelParams == actual.levelParams && expected.type == actual.type
        && reference.modules[name]? == submission.modules[name]?
    | _ => false

def check (env : Environment) (reference submission : Loaded) (allowed : NameSet)
    (name : Name) : Json :=
  let result : Except String (Array Name) := do
    let some expected := reference.constants[name]?
      | throw "theorem is not in the reference build"
    let some actual := submission.constants[name]? | throw "theorem is missing"
    unless actual matches .thmInfo _ do throw "target is not a theorem"
    unless (env.find? name).isSome do throw "theorem did not pass the kernel"
    unless expected.levelParams == actual.levelParams && expected.type == actual.type do
      throw "theorem statement changed"
    let _ ← (expected.type.getUsedConstants.forM
      (sameStatement reference.constants submission.constants)).run {}
    -- Everything the proof rests on that the reference also declares, including the
    -- definitions a trusted axiom's statement mentions, must be the reference's own.
    for used in closureNames submission.constants #[name] do
      if let (some e, some a) := (reference.constants[used]?, submission.constants[used]?) then
        sameConstant e a
    let axioms := axiomsOf env name
    if let some bad := axioms.find? (!allowed.contains ·) then
      throw s!"uses axiom {bad}"
    if let some impostor := axioms.find? (!trustedAxiom reference submission ·) then
      throw s!"axiom {impostor} is not the reference declaration"
    return axioms
  match result with
  | .ok axioms => Json.mkObj [("theorem", toJson name), ("ok", true),
      ("axioms", toJson (axioms.map toString))]
  | .error reason => Json.mkObj [("theorem", toJson name), ("ok", false), ("reason", reason)]

def failed (theorems : Array Name) (reason : String) : Array Json :=
  theorems.map fun name =>
    Json.mkObj [("theorem", toJson name), ("ok", false), ("reason", reason)]

/-- Replay the targets' closure once; if the kernel rejects it, replay each target alone. -/
def checkSubmission (reference submission : Loaded) (allowed : NameSet)
    (theorems : Array Name) : IO (Array Json) := do
  let base ← importModules submission.core {}
  let present := theorems.filter submission.constants.contains
  match ← (base.replay (restrict submission.constants present)).toBaseIO with
  | .ok env => return theorems.map (check env reference submission allowed)
  | .error _ =>
    theorems.mapM fun name => do
      match ← (base.replay (restrict submission.constants #[name])).toBaseIO with
      | .ok env => return check env reference submission allowed name
      | .error error => return Json.mkObj [("theorem", toJson name), ("ok", false),
          ("reason", s!"kernel replay failed: {error}")]

def strings (value : Json) (key : String) : IO (Array String) :=
  match value.getObjValAs? (Array String) key with
  | .ok result => pure result
  | .error error => throw <| IO.userError s!"request field {key}: {error}"

def main (arguments : List String) : IO UInt32 := do
  let [nonce, requestPath] := arguments
    | throw <| IO.userError "usage: <nonce> <request.json>"
  let request ← IO.ofExcept <| Json.parse (← IO.FS.readFile requestPath)
  let sysroot ← findSysroot
  let core : SearchPath := [sysroot / "lib" / "lean"]
  let submissionPath : SearchPath := (← strings request "submission_libraries").toList.map (⟨·⟩)
  let referencePath : SearchPath := (← strings request "reference_libraries").toList.map (⟨·⟩)
  let roots := (← strings request "roots").map String.toName
  let theorems := (← strings request "theorems").map String.toName
  let allowed := (← strings request "allowed_axioms").foldl
    (fun set name => set.insert name.toName) NameSet.empty
  initSearchPath sysroot
  let reference ← match ← (loadAll core referencePath roots).toBaseIO with
    | .ok loaded => pure loaded
    | .error error =>
      IO.eprintln s!"reference build did not load: {error}"
      IO.println s!"ANARRES-AXIOM-CHECK-REFERENCE-ERROR {nonce}"
      return 3
  let results ← match ← (loadAll core submissionPath roots).toBaseIO with
    | .error error => pure (failed theorems s!"submission did not load: {error}")
    | .ok submission => checkSubmission reference submission allowed theorems
  for result in results do
    IO.println result.compress
  IO.println s!"ANARRES-AXIOM-CHECK-COMPLETE {nonce} {results.size}"
  return 0

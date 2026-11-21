import Lean

/-!
Trusted axiom and statement check for fresh Vero grading.

Vero reads its axiom report from Lake output, and any model code that runs while a
model module is built or imported can forge that output. This checker never imports a
model module. It reads the compiled `.olean` files as data, sends every non-core
declaration back through the kernel, computes axioms from the kernel-checked
environment, and requires each target theorem's statement, with every protected
definition the statement depends on, to equal a reference build of the untouched task.

Usage: `lean --run AnarresAxiomCheck.lean <nonce> <request.json>`, where the request
names the submission and reference library directories, the root modules, the target
theorems, and the allowed axioms. It prints one JSON object per theorem and a final
line `ANARRES-AXIOM-CHECK-COMPLETE <nonce> <count>`.
-/

open Lean

structure Loaded where
  constants : Std.HashMap Name ConstantInfo := {}
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
    modify fun s => { s with constants := s.constants.insert info.name info }

def loadAll (core libraries : SearchPath) (roots : Array Name) : IO Loaded := do
  let (_, loaded) ← (roots.forM (load core libraries)).run {}
  return loaded

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

def axiomsOf (env : Environment) (name : Name) : Array Name :=
  let (_, state) := ((CollectAxioms.collect name).run env).run {}
  state.axioms

def check (env : Environment) (reference submission : Std.HashMap Name ConstantInfo)
    (allowed : NameSet) (name : Name) : Json :=
  let result : Except String (Array Name) := do
    let some expected := reference[name]? | throw "theorem is not in the reference build"
    let some actual := submission[name]? | throw "theorem is missing"
    unless actual matches .thmInfo _ do throw "target is not a theorem"
    unless (env.find? name).isSome do throw "theorem did not pass the kernel"
    unless expected.levelParams == actual.levelParams && expected.type == actual.type do
      throw "theorem statement changed"
    let _ ← (expected.type.getUsedConstants.forM
      (sameStatement reference submission)).run {}
    let axioms := axiomsOf env name
    if let some bad := axioms.find? (!allowed.contains ·) then
      throw s!"uses axiom {bad}"
    return axioms
  match result with
  | .ok axioms => Json.mkObj [("theorem", toJson name), ("ok", true),
      ("axioms", toJson (axioms.map toString))]
  | .error reason => Json.mkObj [("theorem", toJson name), ("ok", false), ("reason", reason)]

def checkGroup (core submissionPath referencePath : SearchPath) (allowed : NameSet)
    (roots theorems : Array Name) : IO (Array Json) := do
  let failed (reason : String) : Array Json := theorems.map fun name =>
    Json.mkObj [("theorem", toJson name), ("ok", false), ("reason", reason)]
  let reference ← loadAll core referencePath roots
  match ← (loadAll core submissionPath roots).toBaseIO with
  | .error error => return failed s!"submission did not load: {error}"
  | .ok submission =>
    let base ← importModules submission.core {}
    match ← (base.replay submission.constants).toBaseIO with
    | .ok env => return theorems.map (check env reference.constants submission.constants allowed)
    | .error error => return failed s!"kernel replay failed: {error}"

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
  let allowed := (← strings request "allowed_axioms").foldl
    (fun set name => set.insert name.toName) NameSet.empty
  let groups ← IO.ofExcept <| request.getObjValAs? (Array Json) "groups"
  initSearchPath sysroot
  let mut count := 0
  -- Each axiom-check file is checked alone, as Vero grades it, so one module that
  -- failed to build fails only the theorems that depend on it.
  for group in groups do
    let roots := (← strings group "roots").map String.toName
    let theorems := (← strings group "theorems").map String.toName
    for result in ← checkGroup core submissionPath referencePath allowed roots theorems do
      IO.println result.compress
      count := count + 1
  IO.println s!"ANARRES-AXIOM-CHECK-COMPLETE {nonce} {count}"
  return 0
